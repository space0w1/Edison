from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, forwards


def create_app() -> FastAPI:
    app = FastAPI(
        title="Edison API",
        description="API for Edison project (An energy pricing engine)",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(forwards.router, prefix="/api/v1", tags=["Forwards"])
    return app