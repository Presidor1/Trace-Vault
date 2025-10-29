# tracevault/osint/scrapers/twitter_searcher.py

import json
import logging
import sys
import numpy as np
from scipy.spatial.distance import cosine
from typing import Dict, Any, List, Optional
import requests # Keeping this for potential future API calls

# --- Project Imports ---
from logs.logger import get_logger

# --- Setup ---
logger = get_logger(__name__)

# --- Configuration ---
# Threshold: Cosine similarity score (lower is more similar for cosine distance)
# A typical threshold for facial verification (e.g., FaceNet)
SIMILARITY_THRESHOLD = 0.45 

# --- SIMULATED OSINT Database ---
# In a real system, this would be a massive, indexed table in your database 
# populated by dedicated, continuous OSINT scrapers.
SIMULATED_OSINT_DB = [
    {
        "osint_id": "twitter_1",
        "platform": "Twitter",
        "source_url": "https://twitter.com/jdoe_account",
        "profile_name": "John Doe",
        # 512-dimensional embedding vector (Facenet standard)
        "embedding": np.random.rand(512).tolist(), 
        "bio": "Tech enthusiast and security researcher."
    },
    {
        "osint_id": "twitter_2",
        "platform": "Twitter",
        "source_url": "https://twitter.com/sresearcher",
        "profile_name": "Sarah Researcher",
        # Highly similar vector to the search target (for a guaranteed match in test)
        "embedding": (np.random.rand(512) * 0.1 + np.ones(512) * 0.9).tolist(), 
        "bio": "Forensics expert."
    },
    {
        "osint_id": "twitter_3",
        "platform": "Twitter",
        "source_url": "https://twitter.com/rndm_user",
        "profile_name": "Random User",
        "embedding": np.random.rand(512).tolist(),
        "bio": "I like cats."
    },
]


# --- Core Service: Face Matching ---

def compare_embeddings(target_embedding: List[float]) -> List[Dict[str, Any]]:
    """
    Compares a target face embedding against a database of OSINT embeddings.

    Args:
        target_embedding (List[float]): The 512D embedding vector from a piece of evidence.

    Returns:
        List[Dict[str, Any]]: A ranked list of matching OSINT profiles.
    """
    if not target_embedding:
        logger.warning("Target embedding is empty.")
        return []

    target_np = np.array(target_embedding)
    matches = []

    # Iterate through the simulated OSINT database
    for profile in SIMULATED_OSINT_DB:
        osint_embedding_np = np.array(profile["embedding"])
        
        # Calculate the Cosine Distance
        # Cosine distance ranges from 0 (perfect match) to 2 (opposite vectors).
        # We use the standard definition where 0 means identical.
        distance = cosine(target_np, osint_embedding_np)
        
        # Check against the similarity threshold
        if distance < SIMILARITY_THRESHOLD:
            # Calculate Similarity (1 - distance)
            similarity_score = 1 - distance
            
            match_data = {
                "osint_id": profile["osint_id"],
                "platform": profile["platform"],
                "profile_name": profile["profile_name"],
                "source_url": profile["source_url"],
                "similarity_score": round(similarity_score, 4), # Higher is better
                "distance": round(distance, 4) # Lower is better
            }
            matches.append(match_data)

    # Rank results by similarity score (descending)
    matches.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    logger.info(f"Completed face comparison. Found {len(matches)} matches above threshold {SIMILARITY_THRESHOLD}.")
    
    return matches


def search_twitter_by_face(target_embedding: List[float], evidence_id: str) -> str:
    """
    Worker wrapper to orchestrate the face-based OSINT search.

    Args:
        target_embedding (List[float]): The vector of the face to search for.
        evidence_id (str): The ID of the evidence being analyzed.

    Returns:
        str: A JSON string containing the structured results.
    """
    
    logger.info(f"Starting Twitter OSINT search for evidence {evidence_id}.")
    
    # 1. Compare the target embedding against the database
    matches = compare_embeddings(target_embedding)
    
    if not matches:
        status = "success"
        message = "No matching profiles found on Twitter (simulated DB)."
    else:
        status = "success"
        message = f"Found {len(matches)} potential Twitter profiles."

    final_report = {
        "status": status,
        "message": message,
        "search_platform": "Twitter",
        "evidence_id": evidence_id,
        "matches": matches
    }
    
    return json.dumps(final_report, indent=2)


# --- Test Block ---
if __name__ == "__main__":
    """
    Usage: python osint/scrapers/twitter_searcher.py
    (Uses a pre-defined vector for testing).
    """
    print("--- Running Simulated Twitter Scraper Test ---")
    
    # Test vector: Highly similar to osint_id 'twitter_2' due to the way 
    # the simulated DB was constructed (np.ones() based).
    test_embedding = (np.random.rand(512) * 0.05 + np.ones(512) * 0.95).tolist() 
    
    results_json = search_twitter_by_face(test_embedding, "TEST_EVIDENCE_123")
    
    print("--- Results ---")
    print(results_json)
    print("--- Test Complete ---")

