import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import ScrapePapers from "./pages/ScrapePapers";
import SearchPapers from "./pages/SearchPapers";
import "./styles.css";

function App() {
  return (
    <Router>
      <div className="app-container">
        <header className="app-header">
          <h1 className="app-title">Working Paper Tools</h1>
          <nav className="nav-buttons">
            <Link to="/scrape" className="nav-button">Scrape</Link>
            <Link to="/" className="nav-button">Search</Link>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<SearchPapers />} /> {/* Default to search */}
            <Route path="/scrape" element={<ScrapePapers />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
