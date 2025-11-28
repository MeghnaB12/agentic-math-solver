import React, { useState } from 'react';
import './App.css'; // We'll add some basic styles
import ReactMarkdown from 'react-markdown'; // For rendering math
import remarkMath from 'remark-math'; // For rendering math
import rehypeKatex from 'rehype-katex'; // For rendering math
import 'katex/dist/katex.min.css'; // KaTeX CSS

function App() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading || !question.trim()) return;

    setIsLoading(true);
    setLastResponse(null);
    const userMessage = { sender: 'user', content: question };
    setChatHistory((prev) => [...prev, userMessage]);

    try {
      const res = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();

      let botMessage;
      if (data.error) {
        botMessage = { sender: 'bot', content: `Error: ${data.error}` };
      } else {
        botMessage = { sender: 'bot', content: data.solution, source: data.source };
        setLastResponse({
          question: question,
          solution: data.solution,
        });
      }
      setChatHistory((prev) => [...prev, botMessage]);
    
    } catch (error) {
      const errorMessage = { sender: 'bot', content: `Failed to connect to backend: ${error.message}` };
      setChatHistory((prev) => [...prev, errorMessage]);
    }

    setIsLoading(false);
    setQuestion('');
  };

  const handleFeedback = async (is_correct) => {
    if (!lastResponse) return;

    try {
      await fetch('http://localhost:8000/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: lastResponse.question,
          solution: lastResponse.solution,
          is_correct: is_correct,
        }),
      });
    } catch (error) {
      console.error("Failed to send feedback:", error);
    }
    
    // Hide feedback buttons after click
    setLastResponse(null); 
  };

  return (
    <div className="App">
      <header>
        <h1>Math Professor Agent 🧠</h1>
      </header>
      <div className="chat-window">
        {chatHistory.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {/* Use ReactMarkdown to render math formulas */}
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
            >
              {msg.content}
            </ReactMarkdown>
            {msg.source && <em className="source">(Source: {msg.source})</em>}
          </div>
        ))}
        {isLoading && <div className="message bot">Thinking...</div>}
      </div>
      
      {/* Feedback buttons */}
      {lastResponse && (
        <div className="feedback-container">
          <span>Was this helpful?</span>
          <button onClick={() => handleFeedback(true)}>👍</button>
          <button onClick={() => handleFeedback(false)}>👎</button>
        </div>
      )}

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a math question..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? '...' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default App;