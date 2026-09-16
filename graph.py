from typing import TypedDict, List, Annotated, Literal
import operator
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from nlp_utils import extract_and_negate_symptoms
import re

class CTASAssessment(BaseModel):
    ctas_level: Literal[1, 2, 3, 4, 5] = Field(..., description="CTAS acuity level 1 to 5")
    clinical_rationale: str = Field(..., description="Justification based on active findings")
    urgency_score: float = Field(..., ge=0.0, le=1.0)

class ClinicalState(TypedDict):
    patient_id: str
    raw_input_text: str
    detected_language: str
    conversation_history: Annotated[List[str], operator.add]
    extracted_symptoms: List[str]
    negated_conditions: List[str]
    historical_conditions: List[str]
    triage_assessment: CTASAssessment
    verification_status: Literal["PASSED", "FLAGGED_FOR_REVIEW", "HALLUCINATION_DETECTED"]
    retry_count: int

def ingestion_and_negation_node(state: ClinicalState) -> dict:
    nlp_results = extract_and_negate_symptoms(state["raw_input_text"])
    return {
        "extracted_symptoms": nlp_results["active_symptoms"],
        "negated_conditions": nlp_results["negated_conditions"],
        "historical_conditions": nlp_results["historical_conditions"],
        "conversation_history": ["LLM extraction complete. Slang and temporal negations handled."]
    }

def ctas_triage_node(state: ClinicalState) -> dict:
    raw_text = state["raw_input_text"].lower()
    active = [s.lower() for s in state.get("extracted_symptoms", [])]
    active_str = " ".join(active)
    
    test_patterns = ["test", "testing", "hello", "1 2 3", "one two three", "mic check"]
    is_mic_test = any(p in raw_text for p in test_patterns)
    
    if len(active) == 0 and is_mic_test:
        assessment = CTASAssessment(
            ctas_level=5,
            clinical_rationale="SYSTEM REJECT: Microphone test or non-clinical input detected. Please provide a valid physiological symptom presentation.",
            urgency_score=0.0
        )
    elif len(active) == 0 and len(state.get("negated_conditions", [])) == 0 and len(state.get("historical_conditions", [])) == 0:
        assessment = CTASAssessment(
            ctas_level=5,
            clinical_rationale="SYSTEM REJECT: Input lacks specific physiological symptoms. Please describe the exact pain or discomfort clearly.",
            urgency_score=0.0
        )
    else:
        emergent_indicators = ["chest pain", "abdominal pain", "severe", "shortness of breath", "breathlessness", "crushing", "sweating"]
        urgent_indicators = ["fever", "vomiting", "headache", "nausea", "dizziness"]
        
        if any(ind in active_str for ind in emergent_indicators):
            assessment = CTASAssessment(
                ctas_level=2,
                clinical_rationale="Emergent condition: Active physiological distress or acute pain identified.",
                urgency_score=0.88
            )
        elif any(ind in active_str for ind in urgent_indicators):
            assessment = CTASAssessment(
                ctas_level=3,
                clinical_rationale="Urgent presentation: Moderate active symptoms requiring prompt clinical review.",
                urgency_score=0.60
            )
        elif len(active) > 0:
            assessment = CTASAssessment(
                ctas_level=4,
                clinical_rationale="Less urgent: Mild or isolated complaints without acute distress.",
                urgency_score=0.30
            )
        else:
            assessment = CTASAssessment(
                ctas_level=5,
                clinical_rationale="Non-urgent: Prior symptoms resolved or exclusively negated conditions reported.",
                urgency_score=0.10
            )
            
    return {
        "triage_assessment": assessment,
        "conversation_history": [f"Assigned CTAS Level {assessment.ctas_level}."]
    }

def independent_verifier_node(state: ClinicalState) -> dict:
    assessment = state.get("triage_assessment")
    if assessment.ctas_level <= 2 and len(state.get("extracted_symptoms", [])) == 0:
        status = "HALLUCINATION_DETECTED"
    else:
        status = "PASSED"
        
    return {
        "verification_status": status,
        "conversation_history": [f"Audit completed: {status}"]
    }

def verification_router(state: ClinicalState) -> str:
    if state["verification_status"] == "HALLUCINATION_DETECTED" and state.get("retry_count", 0) < 2:
        return "retry"
    return "pass"

def build_clinical_graph():
    workflow = StateGraph(ClinicalState)
    workflow.add_node("ingestion", ingestion_and_negation_node)
    workflow.add_node("ctas_triage", ctas_triage_node)
    workflow.add_node("verifier", independent_verifier_node)
    
    workflow.add_edge(START, "ingestion")
    workflow.add_edge("ingestion", "ctas_triage")
    workflow.add_edge("ctas_triage", "verifier")
    workflow.add_conditional_edges("verifier", verification_router, {"retry": "ctas_triage", "pass": END})
    
    return workflow.compile(checkpointer=MemorySaver())

clinical_app_graph = build_clinical_graph()