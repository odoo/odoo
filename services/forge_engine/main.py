from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI

if __package__ in {None, ""}:
    services_root = Path(__file__).resolve().parent.parent
    if str(services_root) not in sys.path:
        sys.path.insert(0, str(services_root))
    from forge_engine.db.models import prepare_registry
    from forge_engine.routers.modules import router as modules_router
    from forge_engine.routers.pipeline import router as pipeline_router
else:
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
