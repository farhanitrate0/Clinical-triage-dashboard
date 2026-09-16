FROM python:3.10-slim

# Install system dependencies, specifically FFmpeg for audio processing
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your project files into the container
COPY . .

# Launch FastAPI in the background (internal port 8000) 
# and Streamlit in the foreground (public Render $PORT)
CMD uvicorn api:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port $PORT --server.address 0.0.0.0