from fastapi import FastAPI
from app.api.routes.muhurat import router as muhurat_router

app = FastAPI(title="Baby Name MVP API")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(muhurat_router, prefix="/api/v1")