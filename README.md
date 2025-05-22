
# Working Paper Search

A full‐stack application for scraping U.S. Census Bureau working papers, indexing them with FAISS/Sentence-Transformers, and serving a React frontend via Flask.

---

## Table of Contents

1. [Prerequisites](#prerequisites)  
2. [Unpack the Project](#unpack-the-project)  
3. [Run the Scraper](#run-the-scraper)  
4. [Backend Setup (Flask API)](#backend-setup-flask-api)  
5. [Frontend Setup (React + Vite)](#frontend-setup-react--vite)  
6. [Configuration](#configuration)  
7. [Usage](#usage)  
8. [Troubleshooting](#troubleshooting)  

---

## Prerequisites

- **Python 3.8+**  
- **Node.js (v16+)** & **npm**  
- **Google Chrome** & **ChromeDriver** (for Selenium-based scraping)  
  - Mac: `brew install --cask chromedriver`  
  - Ubuntu: `sudo apt-get install chromium-chromedriver`  
- (Optional) `git` for version control  

---

## Unpack the Project

Download or clone the repo, then unzip (if you have a `.zip`):

```bash
unzip app.zip     # or: git clone <repo-url>
```

Your folder structure should look like:

```
app/
  backend/
    main.py
    scraper.py
    requirements.txt
  frontend/
    package.json
    src/
  scraper.py         # top-level convenience script
```

---

## Run the Scraper

This collects (and optionally downloads) paper metadata before you start the API.

1. **Create & activate** a Python virtual environment:

    ```bash
    cd app
    python3 -m venv venv
    source venv/bin/activate    # Mac/Linux
    venv\Scripts\activate.bat   # Windows
    ```

2. **Install scraper dependencies**:

    ```bash
    pip install requests pandas selenium beautifulsoup4 tqdm
    ```

3. **(Optional)Run the scraper** (If you want an updated dataset, otherwise working_papers_complete works.):

    ```bash
    python scraper.py \
      --output-csv working_papers_complete.csv \
      --download-dir downloads/ \
      --save-interval 10
    ```

4. **(Optional)** If you also want to download PDFs/CSVs, add the flag:

    ```bash
    python scraper.py --download-files
    ```

---

## Backend Setup (Flask API)

1. **Enter** the backend folder:

    ```bash
    cd backend
    ```

2. **Activate** your virtual environment (reuse the one from above or create a new one):
This is for if you activated venv at project root like above, if you did it somwehere else do source (wherever you started)
    ```bash
    source ../venv/bin/activate
    ```

3. **Install** API dependencies:

    ```bash
    pip install -r requirements.txt
    pip install flask-cors
    ```

4. **Start** the Flask server:

    ```bash
    python main.py
    ```

   By default it will run on <http://localhost:5050> in debug mode.

---

## Frontend Setup in a SEPERATE terminal instance (React + Vite)

1. **Open a seperate terminal instance** and enter the frontend folder:

    ```bash
    cd ../frontend
    ```

2. **Install** Node packages(if you don't have NPM you might have to install NPM):

    ```bash
    npm install
    ```

3. **Run** the development server:

    ```bash
    npm install react react-dom react-router-dom framer-motion
    npm install --save-dev vite @vitejs/plugin-react
    npm run dev
    ```

   The app will spin up at <http://localhost:5173> and proxy API calls to your Flask backend.

---

## Configuration

- **Backend URL**  
  If your API is on a different host/port, open `src/config.js` and update:

  ```js
  const BACKEND_URL = "http://localhost:5050";
  ```

- **Ports**  
  - Flask: default `5050`  
  - Vite: default `5173`  

---

## Usage - after first setup its a lot easier

1. Make sure **scraper** has produced `working_papers_complete.csv` (and downloads/, if used).  
2. Start **Flask** (`python main.py`).  
3. Start **React** (`npm run dev`).  
4. Open <http://localhost:5173> and begin scraping or searching papers via the UI.

---

## Troubleshooting

- **ChromeDriver errors**: Ensure your ChromeDriver version matches your Chrome browser.  
- **Port conflicts**: If `5050` or `5173` are in use, either stop conflicting processes or run on alternate ports and update `config.js`.  
- **Missing modules**: If you see `ModuleNotFoundError`, re-run the relevant `pip install` or `npm install` command in the correct folder.  

---

hope you endjoy :3
