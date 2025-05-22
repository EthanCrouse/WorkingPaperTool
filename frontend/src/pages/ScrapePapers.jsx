import React, { useState } from "react";
import { Link } from "react-router-dom";

export default function ScrapePapers() {
  const [downloadFiles, setDownloadFiles] = useState(false);
  const [saveInterval, setSaveInterval] = useState(10);
  const [outputCsv, setOutputCsv] = useState("working_papers_complete.csv");
  const [tempCsv, setTempCsv] = useState("temp_output.csv");
  const [downloadDir, setDownloadDir] = useState("downloads");
  const [retryAttempts, setRetryAttempts] = useState(3);

  const [scrapeOutput, setScrapeOutput] = useState("");
  const [scrapeError, setScrapeError] = useState("");

  const handleScrape = async (e) => {
    e.preventDefault();
    setScrapeOutput("");
    setScrapeError("");

    try {
      const res = await fetch("http://localhost:5050/api/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          download_files: downloadFiles,
          save_interval: saveInterval,
          output_csv: outputCsv,
          temp_csv: tempCsv,
          download_dir: downloadDir,
          retry_attempts: retryAttempts,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setScrapeOutput(data.stdout + "\n" + (data.success ? "CSV found." : "CSV not found."));
        setScrapeError(data.stderr);
      } else {
        setScrapeOutput("");
        setScrapeError(data.stderr || "Scrape failed.");
      }
    } catch (err) {
      console.error(err);
      setScrapeError("An error occurred while scraping.");
    }
  };

  return (
    <div className="page-container">
      <div className="card">
        <h2>Scrape Working Papers</h2>

        <form onSubmit={handleScrape} className="form-group">
          

          <label>
            Save Interval (pages):
            <input
              type="number"
              min="1"
              value={saveInterval}
              onChange={(e) => setSaveInterval(Number(e.target.value))}
            />
          </label>

          <label>
            Output CSV filename:
            <input
              type="text"
              value={outputCsv}
              onChange={(e) => setOutputCsv(e.target.value)}
            />
          </label>

          <label>
            Temporary CSV filename:
            <input
              type="text"
              value={tempCsv}
              onChange={(e) => setTempCsv(e.target.value)}
            />
          </label>

          <label>
            Download directory:
            <input
              type="text"
              value={downloadDir}
              onChange={(e) => setDownloadDir(e.target.value)}
            />
          </label>

          <label>
            Retry attempts:
            <input
              type="number"
              min="1"
              value={retryAttempts}
              onChange={(e) => setRetryAttempts(Number(e.target.value))}
            />
          </label>

          <button type="submit" className="primary-button">Run Scraping</button>
        </form>
      </div>

      <div className="card">
        <h4>Scrape Output</h4>
        <pre>{scrapeOutput}</pre>
        <h4>Scrape Error</h4>
        <pre>{scrapeError}</pre>
      </div>
    </div>
  );
}
