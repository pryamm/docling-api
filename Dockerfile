# Use a CUDA-enabled base image
FROM nvidia/cuda:12.2.2-base-ubuntu22.04

ARG CPU_ONLY=false
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y libgl1 libglib2.0-0 curl wget git procps python3 python3-pip \
    && apt-get clean

# Copy the requirements file to the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch based on the GPU
RUN pip install --no-deps torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

RUN python3 -c "import torch; print(torch.cuda.is_available())"

RUN python3 -c 'from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline; \
    artifacts_path = StandardPdfPipeline.download_models_hf(force=True);'

# Pre-download EasyOCR models
RUN python3 -c 'import easyocr; \
    reader = easyocr.Reader(["en", "id"], gpu=not "$CPU_ONLY".lower() == "true"); \
    print("EasyOCR models downloaded successfully")'

# Copy the application files
COPY . .

# Expose the application port
EXPOSE 8080

# Command to start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
