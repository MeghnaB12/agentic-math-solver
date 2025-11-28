import os
import json
import re
from typing import TypedDict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
from dotenv import load_dotenv

# Load API keys from backend/.env
# This command specifically looks for a .env file in the current directory or parent
load_dotenv() 

# --- 1. Define the Agent's State ---
# This is the "memory" of our agent. It holds all the information
# as it moves from step to step.

class AgentState(TypedDict):
    question: str
    context: Optional[str]
    solution: Optional[str]
    source: str  # 'kb', 'web_search', or 'error'
    error: Optional[str]

# --- 2. Initialize All Our Tools ---

# LLM for generation
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# Embeddings model (must match the one from Week 1)
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# Qdrant client (connects to our Docker database)
qdrant_client = QdrantClient(url="http://localhost:6333")
qdrant = Qdrant(
    client=qdrant_client,
    collection_name="math_kb",
    embeddings=embeddings,
    content_payload_key="question"
)
retriever = qdrant.as_retriever(search_kwargs={"k": 1}) # Get the 1 best match

# Tavily client for web search
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


# --- 3. Define the Graph Nodes (The "Agents") ---
# Each node is a function that performs an action.

def input_guardrail(state: AgentState):
    """
    Node 1: Input Guardrail (FIXED - VERSION 8 - Robust)
    Checks if the question is appropriate.
    """
    print("---NODE: input_guardrail (VERSION 8)---")
    question = state['question']
    
    # 1. Check for PII (Expanded)
    # Checks for SSN (XXX-XX-XXXX) OR Phone (XXX-XXX-XXXX)
    if re.search(r'\d{3}-\d{2}-\d{4}', question) or re.search(r'\d{3}-\d{3}-\d{4}', question):
        print("Guardrail: PII detected in input.")
        return {"error": "Your question contains sensitive information (like a phone number or SSN). Please remove it."}
    
    # 2. Check for non-math questions (Expanded Vocabulary)
    # We added: evaluate, limit, compute, value, find, determine, prove
    math_keywords = [
        'math', 'solve', 'calculate', 'integral', 'matrix', 'algebra', 
        'calculus', 'equation', 'derivative', 'evaluate', 'limit', 
        'compute', 'value', 'find', 'determine', 'prove', 'function',
        'prime', 'number', 'geometry', 'graph'
    ]
    
    # Check if ANY keyword exists in the lowercased question
    if not any(keyword in question.lower() for keyword in math_keywords):
        print("Guardrail: Non-math question rejected.")
        return {"error": "I can only answer math-related questions."}
    
    # If all checks pass
    print("Guardrail: Input OK.")
    return {"error": None}

def retrieve_from_kb(state: AgentState):
    """
    Node 2: Knowledge Base Retriever
    Tries to find a relevant answer in our Qdrant DB.
    """
    print("---NODE: retrieve_from_kb---")
    question = state['question']
    
    # Retrieve the most similar document
    docs = retriever.invoke(question)
    
    # Check if a document was found
    if docs:
        print("Found in KB.")
        # We store the 'question' field from the payload as context
        # because the 'question' *is* the context we want.
        # The payload contains the full row: {'index': ..., 'question': ..., 'gold': ...}
        return {"context": docs[0].page_content, "source": "kb"}
    else:
        print("Not found in KB. Routing to web search.")
        return {"context": None, "source": "web_search"}


def web_search(state: AgentState):
    """
    Node 3: Web Search (MCP-style)
    Searches the web if the KB fails.
    """
    print("---NODE: web_search---")
    question = state['question']
    try:
        # 1. Perform the search
        response = tavily.search(query=f"math problem solution: {question}", search_depth="advanced")
        
        # 2. Create a structured "MCP-style" context object
        mcp_context = {
            "tool_name": "web_search",
            "status": "success",
            "results": [
                {"source_url": r['url'], "snippet": r['content']}
                for r in response['results'][:3] # Get top 3 results
            ]
        }
        # 3. Pass the JSON string as the context
        print("Web search successful.")
        return {"context": json.dumps(mcp_context, indent=2), "source": "web_search"}
    
    except Exception as e:
        print(f"Web search failed: {e}")
        mcp_error = {"tool_name": "web_search", "status": "error", "message": str(e)}
        return {"context": json.dumps(mcp_error), "source": "error", "error": str(e)}


def generate_solution(state: AgentState):
    """
    Node 4: Solution Generator (FIXED)
    Generates the final answer using the LLM.
    """
    print("---NODE: generate_solution---")
    context = state['context']
    question = state['question']
    
    # 1. Create a simple prefix
    if state['source'] == 'web_search':
        context_prefix = "Use the following JSON output from the web search tool:"
    elif state['source'] == 'kb':
        context_prefix = "Use the following context from our knowledge base (a similar question):"
    else:
        context_prefix = "No context was found. Try to answer from your own knowledge."

    # 2. Define the LLM prompt.
    # Notice {context} is now a safe variable INSIDE the template.
    # This prevents the template from trying to read the math symbols.
    system_message = f"""You are a math professor.
    {context_prefix}
    
    CONTEXT:
    {{context}}
    
    ---
    Generate a clear, step-by-step solution to the user's question below.
    If the context is insufficient, state that you cannot provide a reliable answer."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Question:\n{question}\n\nSolution:"),
    ])
    
    # 3. Generate the solution
    chain = prompt | llm
    # The template now correctly expects both 'context' and 'question'
    solution = chain.invoke({"context": context, "question": question})
    print("Solution generated.")
    return {"solution": solution.content}

def output_guardrail(state: AgentState):
    """
    Node 5: Output Guardrail
    Checks the final generated solution.
    """
    print("---NODE: output_guardrail---")
    solution = state['solution']
    
    # 1. Check for refusal
    if "I cannot answer" in solution or "As an AI" in solution:
        print("Guardrail: LLM refusal detected.")
        return {"error": "I was unable to generate a valid solution."}
    
    # If all checks pass
    print("Guardrail: Output OK.")
    return {"error": None}


# --- 4. Define the Graph's Edges (The "Router") ---
# These functions decide which node to go to next.

def check_input_error(state: AgentState):
    """
    Conditional Edge 1:
    After the input guardrail, do we proceed or stop?
    """
    if state.get("error"):
        return "end_error" # Stop immediately
    return "retrieve_from_kb"


def should_search_web(state: AgentState):
    """
    Conditional Edge 2:
    After checking the KB, do we use the KB's context or search the web?
    """
    if state['source'] == "web_search":
        return "web_search"
    else: # source is 'kb'
        return "generate_solution"

# --- 5. Build and Compile the Graph ---

print("Compiling agent graph...")

# 1. Initialize the graph
workflow = StateGraph(AgentState)

# 2. Add all the nodes
workflow.add_node("input_guardrail", input_guardrail)
workflow.add_node("retrieve_from_kb", retrieve_from_kb)
workflow.add_node("web_search", web_search)
workflow.add_node("generate_solution", generate_solution)
workflow.add_node("output_guardrail", output_guardrail)

# 3. Add a special "error" end node
# We use a simple lambda function to just pass the state through
workflow.add_node("end_error", lambda state: state)

# 4. Set the entry point
workflow.set_entry_point("input_guardrail")

# 5. Add the conditional edges (the routing logic)
workflow.add_conditional_edges(
    "input_guardrail",
    check_input_error,
    {
        "end_error": "end_error", # Go to the error end node
        "retrieve_from_kb": "retrieve_from_kb"
    }
)

workflow.add_conditional_edges(
    "retrieve_from_kb",
    should_search_web,
    {
        "web_search": "web_search",
        "generate_solution": "generate_solution"
    }
)

# 6. Add the normal edges
workflow.add_edge("web_search", "generate_solution")
workflow.add_edge("generate_solution", "output_guardrail")
workflow.add_edge("output_guardrail", END) # This is the "success" end
workflow.add_edge("end_error", END)        # This is the "failure" end

# 7. Compile the graph!
math_agent = workflow.compile()

print("Math agent graph compiled successfully!")