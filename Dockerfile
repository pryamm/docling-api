# Use a base image with Python 3.12
FROM python:3.12-slim-bookworm

ARG CPU_ONLY=false
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y redis-server libgl1 libglib2.0-0 curl wget git procps \
    && apt-get clean

# Copy the requirements file to the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch based on the CPU_ONLY flag
RUN if [ "$CPU_ONLY" = "true" ]; then \
    pip install --no-cache-dir torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu; \
    else \
    pip install --no-deps torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    fi

# Environment variables
ENV HF_HOME=/tmp/ \
    TORCH_HOME=/tmp/ \
    OMP_NUM_THREADS=4

# Pre-download models for Docling
RUN python -c 'from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline; \
    artifacts_path = StandardPdfPipeline.download_models_hf(force=True);'

# Pre-download EasyOCR models
RUN python -c 'import easyocr; \
    reader = easyocr.Reader(["fr", "de", "es", "en", "it", "pt"], gpu=True); \
    print("EasyOCR models downloaded successfully")'

# Copy the application files
COPY . .

# Expose the application port
EXPOSE 8080

# Command to start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
