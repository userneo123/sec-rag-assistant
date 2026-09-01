import { useState } from "react";
import "./App.css";

// Your deployed Azure backend. Change this if you ever redeploy elsewhere.
const API_BASE_URL = "https://sec-rag-assistant-hdgbhvbmfhdna3ej.centralindia-01.azurewebsites.net";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setAnswer(null);
    setSources([]);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const data = await response.json();
      setAnswer(data.answer);
      setSources(data.sources);
    } catch (err) {
      setError(
        "Something went wrong reaching the assistant. If this is the first " +
          "request in a while, the server may be waking up from sleep " +
          "(free tier) -- wait 30 seconds and try again."
      );
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>SEC Filing RAG Assistant</h1>
      <p className="subtitle">
        Ask a question about Aster Robotics (ASTR), Bluepeak Analytics (BPKA),
        or Coral Harbor Foods (CHFI) — fiscal year 2025 10-K filings.
      </p>

      <form onSubmit={handleSubmit} className="ask-form">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What was Aster Robotics' revenue in fiscal 2025?"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {answer && (
        <div className="answer-block">
          <h2>Answer</h2>
          <p>{answer}</p>

          {sources.length > 0 && (
            <>
              <h3>Sources</h3>
              <ul className="sources-list">
                {sources.map((s) => (
                  <li key={s.id}>
                    <strong>{s.id}</strong> — {s.company} ({s.ticker}),{" "}
                    {s.filing_type} FY{s.fiscal_year}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
