import json
import time
import sys
from typing import Dict, Any
import httpx
from opentelemetry import trace
from opentelemetry.propagate import inject
from app.metrics import check_up, check_latency_seconds

# INTERVIEW AMMUNITION: OpenTelemetry is preferred over print() logging because it provides structured, trace-context-aware logs and distributed spans that allow developers to correlate performance bottlenecks across complex microservice call graphs, which simple stdout prints cannot do.

tracer = trace.get_tracer("uptime-monitor-checker")

async def check_url(url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    with tracer.start_as_current_span("check_url_span") as span:
        span.set_attribute("http.url", url)
        
        headers = {}
        inject(headers)  # Inject OTel context headers for trace propagation
        
        start_time = time.perf_counter()
        status_code = 0
        up = False
        
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            status_code = response.status_code
            # Consider any 2xx or 3xx status code as up
            up = 200 <= status_code < 400
            span.set_attribute("http.status_code", status_code)
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            status_code = 0
            up = False
        
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        latency_seconds = latency_ms / 1000.0
        
        # Update Prometheus metrics
        check_up.labels(url=url).set(1.0 if up else 0.0)
        check_latency_seconds.labels(url=url).set(latency_seconds)
        
        # Get Span Context for log correlation
        span_context = span.get_span_context()
        trace_id = format(span_context.trace_id, "032x") if span_context.is_valid else "00000000000000000000000000000000"
        
        log_payload = {
            "url": url,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
            "up": up,
            "trace_id": trace_id
        }
        
        # Output structured JSON log to stdout
        print(json.dumps(log_payload), flush=True)
        return log_payload
