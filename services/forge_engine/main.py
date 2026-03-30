from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db.models import prepare_registry
from .routers.modules import router as modules_router
from .routers.pipeline import router as pipeline_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await prepare_registry()
    yield


app = FastAPI(title="Kodoo Forge Engine", version="19.0.1.0.0", lifespan=lifespan)
app.include_router(modules_router, prefix="/modules", tags=["modules"])
app.include_router(pipeline_router, tags=["pipeline"])


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
