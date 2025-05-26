from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os, dotenv

dotenv.load_dotenv()

client = OpenAI(
    api_key="AIzaSyCGenom5_GzoDLBZq-_KujTEodisBWR6OI",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
app = FastAPI(title="Alone I Level Up API")

class QuestRequest(BaseModel):
    goal: str

@app.post("/generate_quest")
async def generate_quest(req: QuestRequest):
    
    # could refine the prompt to make it similar to solo levelling dialogue
    prompt = f"Create one quest for a user working on: {req.goal}"
    response = client.chat.completions.create(
        model="gemini-2.0-flash", 
        messages=[
            {
                "role": "user", 
                "content": prompt
            }
        ],
        max_tokens=100
    )
    return {"quest": response.choices[0].message.content.strip()}

