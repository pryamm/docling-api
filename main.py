from io import BytesIO
from fastapi import FastAPI, APIRouter, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from utils import is_file_format_supported

import time
from docling.datamodel.base_models import InputFormat, DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption, DocumentConverter

from pydantic import BaseModel, Field
from typing import Optional
import torch

class Result(BaseModel):
    text: Optional[str] = Field(None, description="The markdown content of the document")
    data: Optional[dict] = Field(None, description="The JSON content of the document")
    error: Optional[str] = Field(None, description="The error that occurred during the conversion")

class ConverterService:
    def __init__(self, format_options=None):
        self.format_options = format_options
        
        # Check for MPS (Metal Performance Shaders) availability
        self.device = (
            torch.device("mps")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
            else torch.device("cpu")
        )
        print(f"Using device: {self.device}")

    def convert(
        self,
        filename: str,
        file: BytesIO,
    ) -> Result:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        
        # Add MPS configuration
        pipeline_options.ocr_options = {
            "device": self.device,
            "batch_size": 4,  # Adjust based on your memory
        }
        
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        start_time = time.time()
        try:
            conv_result = doc_converter.convert(DocumentStream(name=filename, stream=file))
            end_time = time.time() - start_time

            print(f"Document {filename} converted in {end_time:.2f} seconds.")

            if conv_result.errors:
                return Result(error=conv_result.errors[0].error_message)

            return Result(data=conv_result.document.export_to_dict())

        except Exception as e:
            print(f"Conversion failed: {e}")
            return Result(text="failed")

# Create the FastAPI app
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Set up the document conversion router
router = APIRouter()

# Initialize the custom document converter service
converter_service = ConverterService()

@router.post(
    '/documents/convert',
    response_model=Result,
    response_model_exclude_unset=True,
    description="Convert a single document synchronously",
)
async def convert_single_document(
    document: UploadFile = File(...)
):
    file_bytes = await document.read()
    if not is_file_format_supported(file_bytes, document.filename):
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {document.filename}")

    return converter_service.convert(document.filename, BytesIO(file_bytes))

@router.get("/system-info")
async def get_system_info():
    return {
        "mps_available": hasattr(torch.backends, "mps") and torch.backends.mps.is_available(),
        "current_device": str(converter_service.device),
        "pytorch_version": torch.__version__,
        "is_built_for_mac": torch.backends.mps.is_built(),
    }

# Include the router in the app
app.include_router(router, prefix="", tags=["document-converter"])
