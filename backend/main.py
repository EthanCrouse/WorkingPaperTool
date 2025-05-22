import os
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type'
        }
        return ('', 204, headers)

@app.after_request
def apply_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    return response

# -----------------------------
# Configuration
# -----------------------------
SCRAPED_CSV = "working_papers_complete.csv"
EMBEDS_FILE = "embeddings.npy"
FAISS_INDEX_FILE = "faiss_index.bin"


# Global in-memory cache for data & model
df = None
model = None
index = None
embeddings = None
modelname = "all-MiniLM-L6-v2"

# -----------------------------
# Helper Functions
# -----------------------------
def load_csv(csv_path: str) -> pd.DataFrame:
    data = pd.read_csv(csv_path)
    data['Date Published'] = pd.to_datetime(data['Date Published'], errors='coerce')
    return data

def build_faiss_index(embeds: np.ndarray) -> faiss.IndexFlatIP:
    dimension = embeds.shape[1]
    index_local = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(embeds)
    index_local.add(embeds)
    return index_local

def compute_embeddings(dataframe: pd.DataFrame, model_ref: SentenceTransformer) -> np.ndarray:
    texts = (dataframe["Title"].fillna("") + " " + dataframe["Abstract"].fillna("")).tolist()
    # For large data, chunk if needed. Here we do it directly:
    embed_array = model_ref.encode(texts, show_progress_bar=False)
    embed_array = np.array(embed_array, dtype='float32')
    return embed_array

def load_or_create_embeddings():
    global df, model, index, embeddings
    if df is None:
        return

    if os.path.exists(EMBEDS_FILE) and os.path.exists(FAISS_INDEX_FILE):
        print("Loading existing embeddings and FAISS index from disk...")
        embeddings = np.load(EMBEDS_FILE)
        index = faiss.read_index(FAISS_INDEX_FILE)
    else:
        print("No local embeddings found. Computing embeddings now...")
        embeddings = compute_embeddings(df, model)
        index = build_faiss_index(embeddings)
        np.save(EMBEDS_FILE, embeddings)
        faiss.write_index(index, FAISS_INDEX_FILE)

def run_scraper_script(download_files, save_interval, output_csv, temp_csv, download_dir, retry_attempts):
    # Build the command for the external script
    command = [
        "python", "scraper.py",
        "--save-interval", str(save_interval),
        "--output-csv", output_csv,
        "--temp-csv", temp_csv,
        "--download-dir", download_dir,
        "--retry-attempts", str(retry_attempts)
    ]
    if download_files:
        command.append("--download-files")

    result = subprocess.run(command, capture_output=True, text=True)
    return result

def search_papers(query, authors=None, date_from=None, date_to=None, top_k=5):
    global df, model, index
    if df is None or df.empty or index is None or model is None:
        return []

    if isinstance(authors, str):
        authors = [authors]

    # Encode and normalize query
    query_emb = model.encode([query], show_progress_bar=False)
    query_emb = np.array(query_emb, dtype='float32')
    faiss.normalize_L2(query_emb)

    # Retrieve more than needed, filter afterward
    distances, indices = index.search(query_emb, top_k * 5)
    results = []

    for dist, idx in zip(distances[0], indices[0]):
        row = df.iloc[idx]

        # Filter by authors
        if authors:
            row_authors = [a.strip() for a in str(row['Authors']).split(';')]
            if not any(a in row_authors for a in authors):
                continue

        # Filter by dates
        paper_date = row['Date Published']
        if date_from and paper_date and paper_date < date_from:
            continue
        if date_to and paper_date and paper_date > date_to:
            continue

        results.append({
            "Title": row["Title"],
            "Link": row["Link"],
            "Authors": row["Authors"],
            "DatePublished": str(row["Date Published"]),
            "Abstract": row["Abstract"],
            "Similarity": float(dist)
        })

        if len(results) >= top_k:
            break

    return results

# -----------------------------
# Flask Routes
# -----------------------------
@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.json
    download_files = data.get("download_files", False)
    save_interval = data.get("save_interval", 10)
    output_csv = data.get("output_csv", SCRAPED_CSV)
    temp_csv = data.get("temp_csv", "temp_output.csv")
    download_dir = data.get("download_dir", "downloads")
    retry_attempts = data.get("retry_attempts", 3)

    # Run the external scraping script
    result = run_scraper_script(download_files, save_interval, output_csv, temp_csv, download_dir, retry_attempts)

    # Return the command output
    return jsonify({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": os.path.exists(output_csv)
    })

@app.route("/api/loadData", methods=["GET"])
@app.route("/api/loadData", methods=["GET"])
def load_data():
    """Load data from CSV if it exists, load or create embeddings."""
    global df, model
    if not os.path.exists(SCRAPED_CSV):
        return jsonify({"error": f"CSV file {SCRAPED_CSV} not found."}), 404

    df = load_csv(SCRAPED_CSV)
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')

    load_or_create_embeddings()

    embed_shape = list(embeddings.shape) if embeddings is not None else None
    embed_file_size = os.path.getsize(EMBEDS_FILE) // 1024 if os.path.exists(EMBEDS_FILE) else None

    return jsonify({
        "message": "Data and embeddings loaded successfully.",
        "model": FAISS_INDEX_FILE,
        "embeddings_shape": embed_shape,
        "embeddings_file_kb": embed_file_size
    })



@app.route("/api/recompute", methods=["POST"])
def recompute():
    """Recompute embeddings if needed."""
    global df, model, index, embeddings, modelname
    if df is None:
        return jsonify({"error": "No CSV loaded yet."}), 400
    if model is None:
        model = SentenceTransformer(modelname)

    new_embeddings = compute_embeddings(df, model)
    new_index = build_faiss_index(new_embeddings)
    np.save(EMBEDS_FILE, new_embeddings)
    faiss.write_index(new_index, FAISS_INDEX_FILE)
    embeddings = new_embeddings
    index = new_index

    embed_shape = list(embeddings.shape)
    embed_file_size = os.path.getsize(EMBEDS_FILE) // 1024 if os.path.exists(EMBEDS_FILE) else None

    return jsonify({
        "message": "Embeddings and FAISS index updated successfully.",
        "model": modelname,
        "embeddings_shape": embed_shape,
        "embeddings_file_kb": embed_file_size
    })



@app.route("/api/search", methods=["POST"])
def search_endpoint():
    data = request.json
    query = data.get("query", "")
    authors_filter = data.get("authors")
    date_start = data.get("date_start", None)
    date_end = data.get("date_end", None)
    top_k = data.get("top_k", 5)

    if not query:
        return jsonify([])

    if authors_filter and isinstance(authors_filter, str) and authors_filter.strip():
        authors = [a.strip() for a in authors_filter.split(",")]
    else:
        authors = None

    if date_start:
        # date_start like "2023-01-01"?
        date_from = datetime.fromisoformat(date_start)
    else:
        date_from = None

    if date_end:
        date_to = datetime.fromisoformat(date_end)
    else:
        date_to = None

    results = search_papers(query, authors, date_from, date_to, top_k)
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
