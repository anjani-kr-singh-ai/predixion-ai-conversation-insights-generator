"""
AI Internship Assignment - Conversational Insights Generator

Commands to run:
uvicorn main:app --reload

Test using curl:
curl -X POST http://127.0.0.1:8000/analyze_call \
-H "Content-Type: application/json" \
-d "{\"transcript\": \"Hello, I will pay next week for sure.\"}"
"""

import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv
import asyncpg

# Load .env
load_dotenv()

# ENV Variables
DB_URL = os.getenv("DATABASE_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not DB_URL:
    raise Exception("DATABASE_URL not found in .env")
if not GEMINI_KEY:
    raise Exception("GEMINI_API_KEY not found in .env")

# Pydantic Model
class CallInsight(BaseModel):
    customer_intent: str
    sentiment: Literal['Negative', 'Neutral', 'Positive']
    action_required: bool
    summary: str

# FastAPI App
app = FastAPI(title="Conversational Insights Analyzer")
db = None


# AI Layer - Gemini
from google import genai
client = genai.Client(api_key=GEMINI_KEY)

async def generate_insights(transcript: str) -> CallInsight:
    try:
        prompt = f"""
        Analyze the following call transcript and return ONLY a valid JSON object with these exact fields:
        - customer_intent: string (the main intent/purpose of the customer's call)
        - sentiment: string (must be exactly one of: "Negative", "Neutral", "Positive")
        - action_required: boolean (true if follow-up action is needed)
        - summary: string (brief summary of the call)

        Transcript: {transcript}

        Return only the JSON object, no additional text or formatting:
        """

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if not response.candidates:
            raise Exception("No content returned from LLM")
        content_text = response.candidates[0].content.parts[0].text
        
        content_text = content_text.strip()
        if content_text.startswith('```json'):
            content_text = content_text[7:-3]  
        elif content_text.startswith('```'):
            content_text = content_text[3:-3]  
        
        content_text = content_text.strip()
        # Parse JSON
        data = json.loads(content_text)
        return CallInsight(**data)

    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw content: {content_text if 'content_text' in locals() else 'No content'}")
        raise HTTPException(status_code=500, detail="Invalid JSON response from LLM")
    except Exception as e:
        print("LLM Error:", e)
        raise HTTPException(status_code=500, detail="LLM extraction failed.")




# Startup - PostgreSQL Setup
@app.on_event("startup")
async def startup():
    global db
    db = await asyncpg.connect(DB_URL)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS call_records (
            id SERIAL PRIMARY KEY,
            transcript TEXT NOT NULL,
            intent TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            action_required BOOLEAN NOT NULL,
            summary TEXT NOT NULL
        );
    """)

    print("Database initialized successfully")


# API Endpoint
class TranscriptRequest(BaseModel):
    transcript: str

@app.post("/analyze_call")
async def analyze_call(req: TranscriptRequest):
    insight = await generate_insights(req.transcript)

    result = await db.fetchrow("""
        INSERT INTO call_records (transcript, intent, sentiment, action_required, summary)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """, req.transcript, insight.customer_intent, insight.sentiment,
       insight.action_required, insight.summary)

    return {
        "record_id": result["id"],
        "insights": insight
    }
