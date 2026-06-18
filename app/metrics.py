from prometheus_client import Gauge

# Metric definitions for scraping by Prometheus
check_up = Gauge(
    "check_up",
    "Uptime status of the URL (1 = UP, 0 = DOWN)",
    ["url"]
)

check_latency_seconds = Gauge(
    "check_latency_seconds",
    "HTTP response latency for checking the URL in seconds",
    ["url"]
)
