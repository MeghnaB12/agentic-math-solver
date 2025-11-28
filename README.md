# Agentic Math Professor 🧠

An intelligent AI Math Tutor built with **LangGraph**, **FastAPI**, **React**, and **Google Gemini**.

This agent uses an **Agentic RAG (Retrieval-Augmented Generation)** architecture to solve complex math problems. It intelligently routes queries between a local Knowledge Base (JEE Bench dataset) and Web Search, while strictly enforcing safety guardrails.

![Math Agent Screenshot](https://via.placeholder.com/800x400.png?text=Add+Your+Screenshot+Here)
*(You can replace this link with a screenshot of your actual app!)*

## 🌟 Key Features

* **🧠 Agentic Reasoning:** Uses **LangGraph** to create a cyclic graph that decides whether to answer from memory, search the web, or reject the question.
* **📚 RAG (Retrieval-Augmented Generation):** Connects to a **Qdrant** vector database to retrieve similar math problems for context-aware solving.
* **🛡️ Robust Guardrails:** Custom logic to block PII (Phone numbers, SSNs) and non-math related questions before they reach the LLM.
* **🔢 Beautiful Math Rendering:** Frontend uses `KaTeX` to render complex mathematical formulas perfectly.
* **👍 Human-in-the-Loop:** Integrated feedback mechanism to collect user ratings for future fine-tuning.

## 🛠️ Tech Stack

* **Backend:** Python 3.11, FastAPI, LangGraph, LangChain
* **Frontend:** React, Vite, Tailwind CSS (or Custom CSS)
* **Database:** Qdrant (Vector DB running via Docker)
* **AI Models:** Google Gemini 1.5 Flash (Reasoning), HuggingFace (Embeddings)
* **Tools:** Tavily API (Web Search)

## 🚀 Getting Started

### Prerequisites
* Docker Desktop (for the database)
* Python 3.11
* Node.js & npm

### 1. Clone the Repository
```bash
git clone [https://github.com/MeghnaB12/agentic-math-solver.git](https://github.com/MeghnaB12/agentic-math-solver.git)
cd agentic-math-solver
```

2. Set up the Database (Qdrant)

Make sure Docker is running, then start the container:


docker-compose up -d qdrant


3. Set up the Backend

cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
touch .env

Add your keys to backend/.env:

GOOGLE_API_KEY="your_google_key"
TAVILY_API_KEY="your_tavily_key"
OPENAI_API_KEY="optional_if_using_openai"


Load the Knowledge Base (Run once):

Bash
python ../notebooks/load_kb.py
Start the Server:

Bash
uvicorn main:app --reload
4. Set up the Frontend

Open a new terminal:

Bash
cd frontend
npm install
npm run dev
Visit http://localhost:5173 (or the port shown in your terminal) to start chatting!

🧪 Architecture Flow
Input Guardrail: Checks for PII and topic relevance.

Router: Decides if the question needs the Knowledge Base or Web Search.

Retrieval: Fetches context from Qdrant (if KB) or Tavily (if Web).

Generation: Google Gemini generates a step-by-step solution.

Output Guardrail: Ensures the answer is safe and relevant.

Frontend: Renders the solution with LaTeX formatting.

🤝 Feedback
Feedback is stored in data/feedback_dataset.jsonl to help improve the model in future iterations.


### 💡 Pro Tip for the Image
To make your README look amazing:
1.  Take a screenshot of your running app (like the one you showed me).
2.  Drag and drop that image file directly into the GitHub README editor.
3.  GitHub will automatically upload it and create a link for you!
