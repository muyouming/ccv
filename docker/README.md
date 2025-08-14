# CCV Docker Setup

This directory contains Docker configuration for running CCV with a REST API service.

## Quick Start

From the root CCV directory:

```bash
# Build and run with docker-compose
cd docker
docker-compose up --build
```

The API will be available at:
- http://localhost:8080 - Main API
- http://localhost:8080/docs - Swagger UI Documentation
- http://localhost:8080/redoc - ReDoc Documentation

## Files

- `Dockerfile` - Production Dockerfile that copies source
- `Dockerfile.dev` - Development Dockerfile that mounts source as volumes
- `docker-compose.yml` - Docker Compose configuration with volume mounts
- `api_service.py` - FastAPI REST service
- `requirements.txt` - Python dependencies
- `nginx.conf` - Nginx reverse proxy configuration
- `supervisord.conf` - Process manager configuration
- `swtdetect.c` - SWT text detection binary source
- `entrypoint.sh` - Container startup script
- `client-examples/` - Example API client code

## Development Mode

The development setup mounts the CCV source code as volumes, allowing you to make changes without rebuilding the container:

```bash
docker-compose -f docker-compose.yml up
```

This mounts:
- `../lib` as `/app/ccv/lib` (read-only)
- `../samples` as `/app/ccv/samples` (read-only)

## API Endpoints

- `GET /health` - Health check
- `GET /sample` - Process a sample image
- `POST /detect` - Upload and process an image
- `GET /results/{id}` - Get processing results

## Building for Production

For a production build that includes all source in the image:

```bash
docker build -f Dockerfile -t ccv-text-detection ..
```

Note: Build context must be the parent directory to access lib and samples folders.