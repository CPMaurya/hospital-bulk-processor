"""
Hospital Bulk Processing System
-------------------------------
A FastAPI service that accepts CSV uploads of hospital records
and pushes them into the Hospital Directory API in batches.

Author: Senior Python Developer Assignment
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

app = FastAPI(
    title="Hospital Bulk Processor",
    description="Bulk CSV upload service for the Hospital Directory API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
