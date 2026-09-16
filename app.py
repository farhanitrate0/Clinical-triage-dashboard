import streamlit as st
import requests
import time
import json
from streamlit_mic_recorder import mic_recorder

TRANSCRIBE_URL = "http://127.0.0.1:8000/transcribe"
TRIAGE_STREAM_URL = "http://127.0.0.1:8000/triage-stream"

st.set_page_config(
    page_title="Clinical Triage Dashboard", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #f0f4f8; }
    
    .block-container {
        max-width: 1250px;
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    h1, h2, h3, p, span { color: #1e293b; }
    .st-emotion-cache-16idsys p { margin-bottom: 0px; }
    
    .ctas-alert {
        background-color: #dc2626; 
        color: white;
        border-radius: 6px;
        padding: 16px 20px;
        margin-bottom: 15px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(220, 38, 38, 0.4);
        border: 2px solid #991b1b;
    }
    .ctas-alert-title {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
        opacity: 0.9;
        margin-bottom: 4px;
    }
    .ctas-alert-score {
        font-size: 1.8rem;
        font-weight: 900;
        letter-spacing: 0.5px;
    }
    
    .critical-card {
        background-color: #fff0f0;
        border-left: 5px solid #fa5252;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 12px;
        color: #c92a2a;
    }
    .standard-card {
        background-color: #e7f5ff;
        border-left: 5px solid #228be6;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 12px;
        color: #1864ab;
    }
    .negated-card {
        background-color: #f1f3f5;
        border-left: 5px solid #ced4da;
        padding: 15px;
        border-radius: 4px;
        color: #495057;
        margin-bottom: 12px;
    }
    
    .card-header {
        font-weight: 700;
        margin-bottom: 4px;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "triage_results" not in st.session_state:
    st.session_state.triage_results = None
if "audio_latency" not in st.session_state:
    st.session_state.audio_latency = 0.0
if "llm_latency" not in st.session_state:
    st.session_state.llm_latency = 0.0

patient_id = "PT-1029"

st.markdown("<h2 style='margin-bottom: 0px;'>Patient Triage Dashboard</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 0.9rem; margin-top: -5px;'>Independent Validation UI for CTAS Triage Automation</p>", unsafe_allow_html=True)
st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

col_id, col_status, col_dept = st.columns([1, 1.5, 1])
with col_id:
    st.metric(label="Patient ID", value=patient_id)
with col_status:
    st.metric(label="Priority Status", value="Awaiting Intake")
with col_dept:
    st.metric(label="Department", value="General ER")

st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

intake_col, analysis_col = st.columns([1, 1.3], gap="large")

with intake_col:
    st.markdown("#### Patient Intake")
    
    input_mode = st.radio("Choose Presentation Format:", ["Voice Recording", "Text Presentation"], horizontal=True)
    
    if "Voice Recording" in input_mode:
        audio = mic_recorder(start_prompt="Start Recording", stop_prompt="Stop Recording", key="recorder")
        if audio:
            with st.spinner("Processing local audio pipeline..."):
                files = {"file": ("audio.webm", audio['bytes'], "audio/webm")}
                
                audio_start = time.time()
                
                try:
                    res = requests.post(TRANSCRIBE_URL, files=files)
                    st.session_state.audio_latency = time.time() - audio_start
                    
                    if res.status_code == 200:
                        st.session_state.transcript = res.json().get("transcript", "")
                except Exception as e:
                    st.error(f"Backend failed: {e}")
                    
        st.text_area("Symptom Presentation (Transcribed):", value=st.session_state.transcript, height=120, disabled=True)
    else:
        current_text = st.text_area("Symptom Presentation:", value=st.session_state.transcript, height=120, placeholder="E.g., 55-year-old male, crushing chest pain radiating to the jaw...")
        st.session_state.transcript = current_text
    
    analyze_clicked = st.button("Run Triage Analysis", type="primary", use_container_width=True)

with analysis_col:
    st.markdown("#### AI Clinical Extraction")
    
    if analyze_clicked:
        if not st.session_state.transcript.strip():
            st.warning("Please provide symptom input before analyzing.")
        else:
            with st.spinner("Executing Real-Time Multi-Agent Routing..."):
                animation_placeholder = st.empty()
                
                def render_loop_nodes(step_states):
                    bg_colors = []
                    for s in step_states:
                        if s == "active": bg_colors.append("#228be6")
                        elif s == "success": bg_colors.append("#2b8a3e")
                        elif s == "retry": bg_colors.append("#c92a2a")
                        else: bg_colors.append("#e9ecef")
                        
                    text_colors = ["#ffffff" if s in ["active", "success", "retry"] else "#495057" for s in step_states]
                    
                    html = f"""
                    <div style="display: flex; gap: 6px; margin-bottom: 20px; text-align: center; font-weight: bold; font-size: 0.8rem;">
                        <div style="flex: 1; background-color: {bg_colors[0]}; color: {text_colors[0]}; padding: 8px; border-radius: 4px;">1. Ingest</div>
                        <div style="flex: 1; background-color: {bg_colors[1]}; color: {text_colors[1]}; padding: 8px; border-radius: 4px;">2. Extract</div>
                        <div style="flex: 1; background-color: {bg_colors[2]}; color: {text_colors[2]}; padding: 8px; border-radius: 4px;">3. Triage</div>
                        <div style="flex: 1; background-color: {bg_colors[3]}; color: {text_colors[3]}; padding: 8px; border-radius: 4px;">4. Audit (Verifier)</div>
                    </div>
                    """
                    animation_placeholder.markdown(html, unsafe_allow_html=True)

                render_loop_nodes(["active", "pending", "pending", "pending"])
                
                payload = {"patient_id": patient_id, "raw_text": st.session_state.transcript}
                llm_start = time.time()
                
                try:
                    response = requests.post(TRIAGE_STREAM_URL, json=payload, stream=True)
                    
                    final_state = {
                        "extracted_symptoms": [],
                        "negated_conditions": [],
                        "historical_conditions": [],
                        "conversation_history": [],
                        "triage_assessment": {}
                    }
                    
                    for line in response.iter_lines():
                        if line:
                            chunk = json.loads(line.decode('utf-8'))
                            
                            if "system_error" in chunk:
                                st.error(chunk["system_error"])
                                break
                            if "fast_fail" in chunk:
                                final_state.update(chunk["fast_fail"])
                                render_loop_nodes(["retry", "retry", "retry", "retry"])
                                break
                                
                            for node_name, node_data in chunk.items():
                                if isinstance(node_data, dict):
                                    for k, v in node_data.items():
                                        if k == "conversation_history" and isinstance(v, list):
                                            final_state[k].extend(v)
                                        else:
                                            final_state[k] = v
                                            
                                if node_name == "ingestion":
                                    render_loop_nodes(["success", "active", "pending", "pending"])
                                    
                                elif node_name == "ctas_triage":
                                    render_loop_nodes(["success", "success", "active", "pending"])
                                    time.sleep(0.4) 
                                    render_loop_nodes(["success", "success", "success", "active"])
                                    
                                elif node_name == "verifier":
                                    status = node_data.get("verification_status", "PASSED")
                                    if status == "HALLUCINATION_DETECTED" or "HALLUCINATION" in str(final_state):
                                        render_loop_nodes(["success", "success", "retry", "retry"])
                                        time.sleep(0.8)
                                        render_loop_nodes(["success", "success", "active", "pending"])
                                    else:
                                        render_loop_nodes(["success", "success", "success", "success"])
                                        time.sleep(0.3)
                                        
                    st.session_state.llm_latency = time.time() - llm_start
                    st.session_state.triage_results = final_state
                    animation_placeholder.empty() 
                    
                except Exception as e:
                    render_loop_nodes(["retry", "retry", "retry", "retry"])
                    st.error(f"Streaming connection failed: {e}")
                    animation_placeholder.empty()

    if st.session_state.triage_results:
        data = st.session_state.triage_results
        
        active_symp = data.get("extracted_symptoms", [])
        negated_symp = data.get("negated_conditions", [])
        history = data.get("historical_conditions", [])
        
        triage_assessment = data.get("triage_assessment", {})
        
        raw_level = triage_assessment.get("ctas_level", 3)
        if raw_level == 1: ctas_score = "Level 1 - Resuscitation"
        elif raw_level == 2: ctas_score = "Level 2 - Emergent"
        elif raw_level == 3: ctas_score = "Level 3 - Urgent"
        elif raw_level == 4: ctas_score = "Level 4 - Less Urgent"
        else: ctas_score = "Level 5 - Non Urgent"
            
        remarks = triage_assessment.get("clinical_rationale", "Standard observation recommended. Awaiting physician validation.")
        
        def format_list(item_list):
            return ", ".join(item_list).title() if item_list else "<span style='color:#6c757d; font-style:italic;'>None explicitly reported.</span>"

        st.markdown(f"""
            <div class="ctas-alert">
                <div class="ctas-alert-title">Recommended CTAS Score</div>
                <div class="ctas-alert-score">{ctas_score}</div>
            </div>
            
            <div class="critical-card">
                <div class="card-header">Active Symptoms Detected</div>
                {format_list(active_symp)}
            </div>
            
            <div class="negated-card">
                <div class="card-header">Negated Conditions</div>
                {format_list(negated_symp)}
            </div>
            
            <div class="negated-card">
                <div class="card-header">Historical Context</div>
                {format_list(history)}
            </div>
            
            <div class="standard-card">
                <div class="card-header">Clinical Remarks</div>
                {remarks}
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("View Raw Graph State JSON"):
            st.json(data)
            
    elif not analyze_clicked:
        st.markdown("<p style='color: #64748b; font-style: italic; margin-top: 10px;'>Awaiting input data. Graph output will render here.</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### System Telemetry")
    st.markdown("---")
    
    audio_color = "normal" if st.session_state.audio_latency < 3.0 else "inverse"
    llm_color = "normal" if st.session_state.llm_latency < 4.0 else "inverse"
    
    st.metric(
        label="Audio Pipeline Latency", 
        value=f"{st.session_state.audio_latency:.2f} s",
        delta="Optimal (<3s)" if st.session_state.audio_latency < 3.0 else "High Latency",
        delta_color=audio_color
    )
    
    st.metric(
        label="LangGraph Exec Time", 
        value=f"{st.session_state.llm_latency:.2f} s",
        delta="Optimal (<4s)" if st.session_state.llm_latency < 4.0 else "High Latency",
        delta_color=llm_color
    )
    
    st.markdown("---")
    st.markdown("**Active Modules:**")
    st.markdown("FFmpeg/Pydub Audio")
    st.markdown("FastAPI Shield")
    st.markdown("Real-Time Stream Multi-Routing")