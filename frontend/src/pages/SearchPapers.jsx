import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

export default function SearchPapers() {
  const [lastSearchSource, setLastSearchSource] = useState(null);
  const [query, setQuery] = useState("");
  const [authors, setAuthors] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState([]);
  const [loadError, setLoadError] = useState("");
  const [searchError, setSearchError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

  const handleLoad = async () => {
  setLoadError("");
  setInfoMessage("Loading data...");
  try {
    const res = await fetch("http://localhost:5050/api/loadData");
    const data = await res.json();
    if (res.ok) {
      setInfoMessage(`Loaded ${data.embeddings_shape?.[0] ?? "?"} embeddings from model: ${data.model}`);
    } else {
      setInfoMessage("");
      setLoadError(data.error || "Failed to load data.");
    }
  } catch (err) {
    setLoadError("Error connecting to server.");
    console.error(err);
  }
};

const handleRecompute = async () => {
  setInfoMessage("Recomputing embeddings...");
  setSearchError("");
  try {
    const res = await fetch("http://localhost:5050/api/recompute", {
      method: "POST"
    });
    const data = await res.json();
    if (res.ok) {
      setInfoMessage(`Recomputed ${data.embeddings_shape?.[0]} embeddings using model: ${data.model}`);
    } else {
      setInfoMessage("");
      setSearchError(data.error || "Failed to recompute embeddings.");
    }
  } catch (err) {
    setSearchError("Error connecting to server.");
    console.error(err);
  }
};

  const handleSearch = async () => {
    setSearchError("");
    setInfoMessage("Searching...");
    try {
      const res = await fetch("http://localhost:5050/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          authors,
          date_start: dateStart || null,
          date_end: dateEnd || null,
          top_k: parseInt(topK),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResults(data);
        setLastSearchSource({ type: "query", value: query });
        setInfoMessage("");
      } else {
        setResults([]);
        setSearchError("Search failed.");
        setInfoMessage("");
      }
    } catch (err) {
      console.error(err);
      setSearchError("Error connecting to server.");
      setInfoMessage("");
    }
  };

  const handleSimilarSearch = async (title, abstractText) => {
    if (!abstractText || typeof abstractText !== "string") return;

    setLastSearchSource({ type: "paper", title, abstract: abstractText });
    setSearchError("");
    setInfoMessage("Searching for similar papers...");

    try {
      const res = await fetch("http://localhost:5050/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: abstractText,
          authors: "",
          date_start: null,
          date_end: null,
          top_k: parseInt(topK),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResults(data);
        setInfoMessage("Found similar papers.");
      } else {
        setResults([]);
        setSearchError("Failed to find similar papers.");
      }
    } catch (err) {
      console.error(err);
      setSearchError("Server error while finding similar papers.");
    }
  };

  return (
    <div className="page-container">
      {/* Nav buttons */}

      <div className="card">
        <h2>Search Working Papers</h2>

        <div className="button-group">
          <button className="primary-button" onClick={handleLoad}>Load Data & Embeddings</button>
          <button className="primary-button" onClick={handleRecompute}>Recompute Embeddings</button>
        </div>

        {loadError && <div className="error">{loadError}</div>}
        {infoMessage && <div className="success">{infoMessage}</div>}

        <div className="form-group">
          <label>Search Query:</label>
          <input value={query} onChange={(e) => setQuery(e.target.value)} />

          <label>Authors (comma separated):</label>
          <input value={authors} onChange={(e) => setAuthors(e.target.value)} />

          <label>Start Date:</label>
          <input type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} />

          <label>End Date:</label>
          <input type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} />

          <label>Number of Results:</label>
          <input type="number" min="1" value={topK} onChange={(e) => setTopK(e.target.value)} />

          <button className="primary-button" onClick={handleSearch}>Search</button>
        </div>
      </div>

      {searchError && <div className="error">{searchError}</div>}

      {/* Display search source info */}
      {lastSearchSource && (
        <div className="search-source">
          {lastSearchSource.type === "query" ? (
            <p>
              <strong>Showing results for:</strong> <em>{lastSearchSource.value}</em>
            </p>
          ) : (
            <>
              <p><strong>Showing results similar to:</strong></p>
              <p><em>{lastSearchSource.title}</em></p>
              <p className="abstract-preview">{lastSearchSource.abstract.slice(0, 160)}...</p>
            </>
          )}
        </div>
      )}

      <div className="results-container">
        <h3>Search Results</h3>
        {results.length === 0 && <div>No results or no search yet.</div>}

        <AnimatePresence>
          {results.map((r, idx) => (
            <motion.div
              key={idx}
              className="card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3, delay: idx * 0.05 }}
            >
              <div>
                <div><strong>Title:</strong> {r.Title}</div>
                <div><strong>Authors:</strong> {r.Authors}</div>
                <div><strong>Date Published:</strong> {r.DatePublished}</div>
                <div><strong>Similarity:</strong> {r.Similarity.toFixed(4)}</div>
                {r.Link && (
                  <div>
                    <a href={r.Link} target="_blank" rel="noreferrer">Link</a>
                  </div>
                )}
                <div><strong>Abstract:</strong> {r.Abstract}</div>
                <button
                  className="primary-button"
                  onClick={() => handleSimilarSearch(r.Title, r.Abstract)}
                >
                  More Like This →
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
