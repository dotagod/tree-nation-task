from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import customers, stats, trees, visits

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="X Visits = 1 Tree",
    description="Track shop visits and plant trees for customers.",
    version="1.0.0",
)

app.include_router(visits.router)
app.include_router(customers.router)
app.include_router(stats.router)
app.include_router(trees.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
