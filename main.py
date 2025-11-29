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
    call_purpose: str
    call_objective_met: bool
    key_results: str
    customer_statements_analysis: str
    non_payment_reasons: str
    sentiment_start: Literal['Negative', 'Neutral', 'Positive']
    sentiment_end: Literal['Negative', 'Neutral', 'Positive']
    overall_sentiment: Literal['Negative', 'Neutral', 'Positive']
    agent_performance_rating: int  # 1-10 scale
    agent_performance_feedback: str
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
        - call_purpose: string (determine the primary purpose of this call - e.g., payment reminder, collection, dispute resolution)
        - call_objective_met: boolean (assess whether the call objective was achieved)
        - key_results: string (identify key outcomes like promises to pay, dispute resolutions, settlement agreements)
        - customer_statements_analysis: string (analyze customer statements for intentions and circumstances)
        - non_payment_reasons: string (identify reasons for non-payment, financial hardships, job loss, etc.)
        - sentiment_start: string (customer sentiment at the beginning - "Negative", "Neutral", or "Positive")
        - sentiment_end: string (customer sentiment at the end - "Negative", "Neutral", or "Positive")
        - overall_sentiment: string (overall call sentiment - "Negative", "Neutral", or "Positive")
        - agent_performance_rating: number (rate agent performance 1-10, where 10 is excellent)
        - agent_performance_feedback: string (feedback on agent's conversation quality, professionalism, problem resolution)
        - action_required: boolean (true if follow-up action is needed)
        - summary: string (comprehensive summary of the call)

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
            call_purpose TEXT NOT NULL,
            call_objective_met BOOLEAN NOT NULL,
            key_results TEXT NOT NULL,
            customer_statements_analysis TEXT NOT NULL,
            non_payment_reasons TEXT NOT NULL,
            sentiment_start TEXT NOT NULL,
            sentiment_end TEXT NOT NULL,
            overall_sentiment TEXT NOT NULL,
            agent_performance_rating INTEGER NOT NULL,
            agent_performance_feedback TEXT NOT NULL,
            action_required BOOLEAN NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        INSERT INTO call_records (transcript, intent, call_purpose, call_objective_met, key_results, 
                                customer_statements_analysis, non_payment_reasons, sentiment_start, 
                                sentiment_end, overall_sentiment, agent_performance_rating, 
                                agent_performance_feedback, action_required, summary)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        RETURNING id
    """, req.transcript, insight.customer_intent, insight.call_purpose, insight.call_objective_met,
       insight.key_results, insight.customer_statements_analysis, insight.non_payment_reasons,
       insight.sentiment_start, insight.sentiment_end, insight.overall_sentiment, 
       insight.agent_performance_rating, insight.agent_performance_feedback, 
       insight.action_required, insight.summary)

    return {
        "record_id": result["id"],
        "insights": insight
    }
