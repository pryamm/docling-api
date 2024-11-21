import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # Enable auto-reload during development
        workers=1,    # Single worker for local development
        limit_concurrency=10
    )