from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_service
import routers


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_service()
    yield


app = FastAPI(title="KMG HR AI Command Center", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "KMG HR AI Command Center is running.",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    service = get_service()
    return {
        "status": "ok",
        "llm_mode": service.llm.provider_name,
        "cache": "hit" if service.cache_hit else "miss",
    }
