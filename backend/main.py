import sys
import uvicorn
from pathlib import Path  # <--- Added missing import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from backend.app.graph import math_agent

app = FastAPI(title="Math Professor Agent API")

# --- UPDATED CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    # Allow both 5173 and 5174, plus localhost generally to be safe
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str = Field(..., description="The math question from the user")

class FeedbackItem(BaseModel):
    question: str
    solution: str
    is_correct: bool
    correction: Optional[str] = None

@app.get("/")
async def root():
    return {"status": "ok", "message": "Math Agent API is running"}

@app.post("/ask")
async def ask_agent(query: Query):
    inputs = {"question": query.question}
    try:
        final_state = math_agent.invoke(inputs)
        return final_state
    except Exception as e:
        return {"error": str(e), "status": "agent_failed"}

@app.post("/feedback")
async def save_feedback(item: FeedbackItem):
    print(f"Received feedback: {item.model_dump_json()}")
    try:
        # We use append mode 'a' to add new lines
        with open("../data/feedback_dataset.jsonl", "a") as f:
            f.write(item.model_dump_json() + "\n")
        return {"status": "feedback received"}
    except Exception as e:
        return {"error": str(e), "status": "save_failed"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)