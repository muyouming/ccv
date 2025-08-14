#!/usr/bin/env python3
"""
CCV SWT Text Detection API Service
A RESTful API service for text detection in images using CCV's SWT algorithm
"""

import os
import json
import uuid
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configuration
UPLOAD_DIR = Path("/app/uploads")
RESULTS_DIR = Path("/app/results")
SWT_BINARY = Path("/app/ccv/bin/swtdetect")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(
    title="CCV Text Detection API",
    description="RESTful API for text detection in images using CCV's Stroke Width Transform (SWT) algorithm",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class DetectionResult(BaseModel):
    """Text detection result model"""
    id: str = Field(description="Unique detection job ID")
    status: str = Field(description="Processing status")
    timestamp: str = Field(description="ISO format timestamp")
    filename: str = Field(description="Original filename")
    regions: List[Dict[str, int]] = Field(default_factory=list, description="Detected text regions")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service status")
    timestamp: str = Field(description="Current timestamp")
    version: str = Field(description="API version")
    swt_available: bool = Field(description="SWT binary availability")

# Utility functions
def cleanup_old_files(directory: Path, max_age_hours: int = 24):
    """Clean up files older than max_age_hours"""
    now = datetime.now()
    for file_path in directory.glob("*"):
        if file_path.is_file():
            file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
            if (now - file_age).total_seconds() > max_age_hours * 3600:
                file_path.unlink()

def parse_swt_output(output: str) -> List[Dict[str, int]]:
    """Parse SWT detection output and extract regions"""
    regions = []
    for line in output.split('\n'):
        if line.strip() and not line.startswith('total'):
            # Parse the output format from swtdetect
            # Expected format: x y width height (space-separated)
            try:
                parts = line.strip().split()
                if len(parts) == 4:
                    region = {
                        'x': int(parts[0]),
                        'y': int(parts[1]),
                        'width': int(parts[2]),
                        'height': int(parts[3])
                    }
                    regions.append(region)
            except (ValueError, IndexError):
                continue
    return regions

def run_swt_detection(image_path: Path) -> Dict[str, Any]:
    """Run SWT detection on an image"""
    start_time = datetime.now()
    
    try:
        # Run swtdetect binary
        result = subprocess.run(
            [str(SWT_BINARY), str(image_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if result.returncode == 0:
            regions = parse_swt_output(result.stdout)
            return {
                'success': True,
                'regions': regions,
                'processing_time': processing_time
            }
        else:
            return {
                'success': False,
                'error': result.stderr or "Detection failed",
                'processing_time': processing_time
            }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': "Detection timeout exceeded",
            'processing_time': 30.0
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'processing_time': (datetime.now() - start_time).total_seconds()
        }

# API Endpoints
@app.get("/", response_model=HealthCheck)
async def root():
    """Root endpoint - health check"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        swt_available=SWT_BINARY.exists()
    )

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        swt_available=SWT_BINARY.exists()
    )

@app.post("/detect", response_model=DetectionResult)
async def detect_text(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(description="Image file to process")
):
    """
    Detect text in an uploaded image
    
    - **file**: Image file (JPEG, PNG, BMP supported)
    - Returns: Detection results with text regions
    """
    
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Validate file type
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Generate unique ID
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    with open(upload_path, "wb") as f:
        f.write(contents)
    
    # Run detection
    detection_result = run_swt_detection(upload_path)
    
    # Schedule cleanup
    background_tasks.add_task(cleanup_old_files, UPLOAD_DIR)
    background_tasks.add_task(cleanup_old_files, RESULTS_DIR)
    
    # Prepare response
    if detection_result['success']:
        return DetectionResult(
            id=job_id,
            status="completed",
            timestamp=timestamp,
            filename=file.filename,
            regions=detection_result['regions'],
            processing_time=detection_result['processing_time']
        )
    else:
        return DetectionResult(
            id=job_id,
            status="failed",
            timestamp=timestamp,
            filename=file.filename,
            regions=[],
            processing_time=detection_result['processing_time'],
            error=detection_result['error']
        )

@app.post("/detect/url", response_model=DetectionResult)
async def detect_text_from_url(url: str, background_tasks: BackgroundTasks):
    """
    Detect text in an image from URL
    
    - **url**: URL of the image to process
    - Returns: Detection results with text regions
    """
    import requests
    
    try:
        # Download image
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="URL does not point to an image")
        
        # Generate unique ID
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        filename = url.split('/')[-1] or 'image.jpg'
        
        # Save image
        upload_path = UPLOAD_DIR / f"{job_id}_{filename}"
        with open(upload_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Run detection
        detection_result = run_swt_detection(upload_path)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_old_files, UPLOAD_DIR)
        
        # Prepare response
        if detection_result['success']:
            return DetectionResult(
                id=job_id,
                status="completed",
                timestamp=timestamp,
                filename=filename,
                regions=detection_result['regions'],
                processing_time=detection_result['processing_time']
            )
        else:
            return DetectionResult(
                id=job_id,
                status="failed",
                timestamp=timestamp,
                filename=filename,
                regions=[],
                processing_time=detection_result['processing_time'],
                error=detection_result['error']
            )
    
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download image: {str(e)}")

@app.get("/sample")
async def get_sample_detection():
    """
    Run detection on a sample image
    
    Returns detection results for a built-in sample image
    """
    sample_path = Path("/app/ccv/samples/street.png")
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample image not found")
    
    detection_result = run_swt_detection(sample_path)
    
    return DetectionResult(
        id="sample",
        status="completed" if detection_result['success'] else "failed",
        timestamp=datetime.now().isoformat(),
        filename="street.png",
        regions=detection_result.get('regions', []),
        processing_time=detection_result['processing_time'],
        error=detection_result.get('error')
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)