# INTERVIEW AMMUNITION: Multi-stage Docker builds are used in production to separate the build dependencies (like compilers and headers) from the final runtime image, minimizing the image size and reducing the security attack surface.

# Stage 1: Build dependencies and wheels
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /root/.local /home/appuser/.local
COPY . /app

# Set PATH to include appuser's local bin
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# Run as non-root user (UID 1000) for security hardening
RUN useradd -u 1000 -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
