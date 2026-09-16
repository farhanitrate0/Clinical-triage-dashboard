import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from graph import clinical_app_graph
import uuid
import io
import json
import speech_recognition as sr
from pydub import AudioSegment

app = FastAPI(title="Clinical Triage API", version="1.0")

class PatientRequest(BaseModel):
    patient_id: str
    raw_text: str

@app.post("/triage")
def run_triage(request: PatientRequest):
    cleaned_text = request.raw_text.strip()
    if len(cleaned_text) < 5:
        return {
            "status": "success",
            "data": {
                "extracted_symptoms": [],
                "negated_conditions": [],
                "historical_conditions": [],
                "triage_assessment": {
                    "ctas_level": 5,
                    "clinical_rationale": "SYSTEM REJECT: Input too short. No clinical symptoms detected."
                }
            }
        }
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "patient_id": request.patient_id,
        "raw_input_text": request.raw_text,
        "detected_language": "en",
        "conversation_history": ["API ingestion started."],
        "extracted_symptoms": [],
        "negated_conditions": [],
        "retry_count": 0
    }
    
    try:
        events = list(clinical_app_graph.stream(initial_state, config, stream_mode="values"))
        return {"status": "success", "data": events[-1]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/triage-stream")
async def stream_triage(request: PatientRequest):
    cleaned_text = request.raw_text.strip()
    if len(cleaned_text) < 5:
        async def fast_fail():
            reject_data = {
                "fast_fail": {
                    "extracted_symptoms": [],
                    "negated_conditions": [],
                    "historical_conditions": [],
                    "triage_assessment": {
                        "ctas_level": 5,
                        "clinical_rationale": "SYSTEM REJECT: Input too short. No clinical symptoms detected."
                    }
                }
            }
            yield (json.dumps(reject_data) + "\n").encode("utf-8")
        return StreamingResponse(fast_fail(), media_type="application/x-ndjson")

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "patient_id": request.patient_id,
        "raw_text": request.raw_text if hasattr(request, "raw_text") else request.raw_text,
        "raw_input_text": request.raw_text,
        "detected_language": "en",
        "conversation_history": ["API ingestion started."],
        "extracted_symptoms": [],
        "negated_conditions": [],
        "retry_count": 0
    }

    def pydantic_encoder(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    async def event_generator():
        try:
            for event in clinical_app_graph.stream(initial_state, config, stream_mode="updates"):
                yield (json.dumps(event, default=pydantic_encoder) + "\n").encode("utf-8")
        except Exception as e:
            yield (json.dumps({"system_error": f"Serialization error: {str(e)}"}) + "\n").encode("utf-8")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    print("\n--- [DEBUG] AUDIO UPLOAD RECEIVED ---")
    try:
        audio_bytes = await file.read()
        try:
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_bytes = wav_io.getvalue()
        except Exception as conv_err:
            wav_bytes = audio_bytes

        temp_filename = "temp_converted_audio.wav"
        with open(temp_filename, "wb") as f:
            f.write(wav_bytes)
            
        r = sr.Recognizer()
        with sr.AudioFile(temp_filename) as source:
            audio_data = r.record(source)
            
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        try:
            transcript_text = r.recognize_google(audio_data, language="en-US")
            return {"transcript": transcript_text}
        except sr.UnknownValueError:
            return {"transcript": "[SYSTEM ERROR: Audio not recognized. Please speak clearly.]"}
        except sr.RequestError as e:
            return {"transcript": "[SYSTEM ERROR: Network connection to speech service failed.]"}
    except Exception as e:
        return {"transcript": "[SYSTEM ERROR: Audio pipeline failure.]"}