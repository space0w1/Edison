from fastapi import FastAPI

from .routes import health


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    return app