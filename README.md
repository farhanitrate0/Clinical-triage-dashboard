# Clinical Triage Dashboard

## Overview
This repository contains the source code for an automated, multi modal clinical triage dashboard. The system is designed to ingest patient symptom presentations via voice or text, extract active and negated medical entities, and assign a standardized urgency score based on the Canadian Triage and Acuity Scale (CTAS). 

Rather than relying solely on raw API calls, the architecture implements a custom, stateful multi-agent workflow combined with deterministic auditing layers to safely process complex clinical presentations, handle multi-lingual slang/negations, and mitigate large language model (LLM) hallucinations.

## Technology Stack
* **Frontend**: Streamlit
* **Backend**: FastAPI, Uvicorn
* **AI & Orchestration**: LangGraph, LangChain, Gemini API (via OpenAI compatibility layer)
* **Audio Processing**: SpeechRecognition, Pydub
* **Machine Learning**: PyTorch, Hugging Face (LoRA, XLM-RoBERTa pipeline)
* **Deployment**: Docker, Render Continuous Deployment

## Key System Features
* **Multi-Modal Ingestion**: Supports raw text input and live audio transcription utilizing standard speech recognition pipelines.
* **Multi-Agent Routing**: Executes a directed graph workflow (`Ingestion` -> `Triage` -> `Verifier`) using LangGraph to manage conversational state and payload data.
* **Independent Verification Node**: Features a deterministic circuit breaker that audits the LLM's output. If an emergent CTAS level (1 or 2) is assigned without corresponding active physiological symptoms, the system flags a hallucination and forces a retry loop.
* **Edge-Case Shielding**: Implements custom prompt engineering contracts and logical routing to safely parse complex linguistic structures (such as transliterated Hinglish and split negations) while rejecting non-clinical inputs like microphone tests.
* **LoRA Fine-Tuning Pipeline**: Includes a proof-of-concept Jupyter notebook establishing a Parameter-Efficient Fine-Tuning (PEFT) pipeline on XLM-RoBERTa for future optimization on structured clinical datasets.

## Repository Structure
* `app.py`: Streamlit frontend UI locked to a clinical light theme.
* `api.py`: FastAPI asynchronous backend handling endpoint routing and audio conversion.
* `graph.py`: LangGraph state definitions, node logic, and conditional edge routing.
* `nlp_utils.py`: Pydantic schemas and LangChain prompting configurations.
* `lora_finetuning.ipynb`: ML training pipeline architecture.
* `Dockerfile`: Production environment configuration.

## Local Development Setup

### Prerequisites
* Python 3.10+
* FFmpeg (required for Pydub audio conversion)

### Environment Variables
The system requires a Gemini API key to function. Create a `.env` file in the root directory:
```text
GOOGLE_API_KEY=your_gemini_api_key_here
