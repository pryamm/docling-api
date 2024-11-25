from io import BytesIO
from fastapi import FastAPI, APIRouter, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from utils import is_file_format_supported

import time
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat, DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption, DocumentConverter
from docling.datamodel.settings import settings 

from pydantic import BaseModel, Field
from typing import Optional

class Result(BaseModel):
    text: Optional[str] = Field(None, description="The markdown content of the document")
    data: Optional[dict] = Field(None, description="The JSON content of the document")
    error: Optional[str] = Field(None, description="The error that occurred during the conversion")

class ConverterService:
    def __init__(self, format_options=None):
        self.format_options = format_options

    def convert(
        self,
        filename: str,
        file: BytesIO,
    ) -> Result:
            
        settings.perf.doc_batch_size = 1 # default 2
        settings.perf.doc_batch_concurrency = 1 # default 2
        settings.perf.page_batch_size = 4 # default 4
        settings.perf.page_batch_concurrency = 4 # default 2

        
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.images_scale = 1.0 # default 1.0
        pipeline_options.ocr_options.use_gpu = True
        pipeline_options.ocr_options.lang = ["en", "id"] # https://www.jaided.ai/easyocr/
        pipeline_options.generate_page_images = False
        pipeline_options.generate_table_images = False
        pipeline_options.generate_picture_images = False

        # Add sequence/batch processing options
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend
                )
            }
        )

        start_time = time.time()
        try:
            doc_stream = DocumentStream(
                name=filename, 
                stream=file,
                input_format=InputFormat.PDF
            )
            
            print(f"Starting conversion with OCR options: {pipeline_options.ocr_options}")
            conv_result = doc_converter.convert(doc_stream)
            end_time = time.time() - start_time

            print(f"Document {filename} converted in {end_time:.2f} seconds.")

            if conv_result.errors:
                error_msg = conv_result.errors[0].error_message
                print(f"Conversion error: {error_msg}")
                return Result(error=error_msg)

            return Result(data=conv_result.document.export_to_dict())

        except Exception as e:
            print(f"Conversion failed with error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            return Result(error=str(e))

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

# Include the router in the app
app.include_router(router, prefix="", tags=["document-converter"])
