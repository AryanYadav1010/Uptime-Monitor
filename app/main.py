import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
import httpx
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.checker import check_url

# Configure OpenTelemetry tracer provider & console span processor
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

# Parse URLs list from environment variable
URLS = [
    url.strip() if url.strip().startswith("http") else f"https://{url.strip()}"
    for url in os.getenv("MONITOR_URLS", "github.com,yelp.com,httpbin.org").split(",")
]

async def check_loop():
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.gather(*(check_url(url, client) for url in URLS), return_exceptions=True)
            await asyncio.sleep(30.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(check_loop())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)

@app.get("/check")
async def trigger_check():
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(check_url(url, client) for url in URLS), return_exceptions=True)
    return {"status": "ok", "results": [r for r in results if not isinstance(r, Exception)]}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health():
    return {"status": "healthy"}
