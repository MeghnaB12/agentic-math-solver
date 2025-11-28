import pandas as pd
from datasets import load_dataset
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import os
import sys

# Ensure Qdrant is running, e.g., via docker-compose
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "math_kb"

# 1. Load Dataset
print("Loading dataset...")
dataset = load_dataset("daman1209arora/jeebench", split="test")
df = dataset.to_pandas()

# Filter for 'math'
math_df = df[df['subject'] == 'math'].reset_index() 
print(f"Found {len(math_df)} math questions.")

# Stop if no questions are found
if len(math_df) == 0:
    print("Error: No math questions found. Check dataset or filter logic.")
    sys.exit(1)


# 2. Initialize Embedder & DB
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2') 
client = QdrantClient(url=QDRANT_URL)

# 3. Create Qdrant Collection
print(f"Recreating collection: {COLLECTION_NAME}")
try:
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=384,  # This MUST match the model's output dimension
            distance=models.Distance.COSINE
        ),
    )
    print("Collection created.")
except Exception as e:
    print(f"Error creating collection: {e}")
    sys.exit(1)


# 4. --- ATOMIC UPLOAD ---
print("Encoding all questions. This may take a minute...")
all_vectors = model.encode(math_df['question'].tolist(), show_progress_bar=True)
print("Encoding complete.")

# Create a list of all points
points = [
    models.PointStruct(
        # --- THIS IS THE FIX ---
        # We use `idx` (0-235) as the ID, not `row['index']`
        id=int(idx), 
        # --- END OF FIX ---
        vector=all_vectors[idx],
        payload=row.to_dict()
    )
    for idx, row in math_df.iterrows()
]

# Upload all points in one single batch
print(f"Uploading all {len(points)} points at once...")
try:
    client.upload_points(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True
    )
    print("Upload complete.")
except Exception as e:
    print(f"Error uploading points: {e}")


# 5. Final Verification
print("Verifying collection count...")
count = client.count(collection_name=COLLECTION_NAME, exact=True)
print(f"Database now contains {count.count} vectors.")