import os
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

if not os.environ.get("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable is missing! Check your .env file.")

class SymptomExtraction(BaseModel):
    active_symptoms: list[str] = Field(
        description="Current, active physical symptoms the patient is experiencing right now. Translate to English."
    )
    negated_conditions: list[str] = Field(
        description="Symptoms the patient explicitly denies having (e.g., 'no chest pain', 'scene hi nhi hai'). Translate to English."
    )
    historical_conditions: list[str] = Field(
        description="Symptoms from the past that have resolved or are no longer active. Translate to English."
    )

def extract_and_negate_symptoms(text: str) -> dict:
    print(f"\n--- [DEBUG] STARTING AI EXTRACTION ---")
    print(f"Input text: {text}")
    try:
        llm = ChatOpenAI(
            model="gemini-3.6-flash", 
            api_key=os.environ.get("GOOGLE_API_KEY"), 
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            temperature=0,
            http_client=httpx.Client(),
            http_async_client=httpx.AsyncClient()
        )
        
        structured_llm = llm.with_structured_output(SymptomExtraction)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert multilingual clinical extraction AI. 
            Read the patient's text and extract symptoms into the exact requested categories. 
            You must deeply understand slang, colloquialisms, transliterated Hinglish, 
            French split negations, and complex double negatives. 
            Always translate the final extracted concepts into standard English medical terms.
            If a category has no symptoms, return an empty list [] for that category.
            
            *** EDGE CASE & NON-CLINICAL INPUT PROTOCOL ***
            If the user input is conversational filler, a microphone test (e.g., 'hello', 'testing 1 2 3', 'is this working'), non-medical in nature, or lacks any physiological symptoms:
            1. DO NOT hallucinate or assume medical symptoms.
            2. Leave the active_symptoms, negated_conditions, and historical_conditions arrays strictly empty []."""),
            ("human", "{text}")
        ])
        
        print("Sending request to Gemini via OpenAI compatibility layer...")
        result = (prompt | structured_llm).invoke({"text": text})
        print(f"Success! Raw API Response: {result}")
        
        return {
            "active_symptoms": result.active_symptoms or [],
            "negated_conditions": result.negated_conditions or [],
            "historical_conditions": result.historical_conditions or []
        }
    except Exception as e:
        print(f"\n[CRITICAL ERROR] The API call failed! Reason:")
        print(str(e))
        print("-------------------------------------------\n")
        return {"active_symptoms": [], "negated_conditions": [], "historical_conditions": []}