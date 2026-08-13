# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# تثبيت أدوات التجميع
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app

# بناء الـ Wheels من المشروع الحالي (pyproject.toml) وكل تبعياته
RUN pip wheel --wheel-dir /build/wheels .

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# تثبيت أدوات الـ OCR والـ PDF (طابق حزمة Odoo للغة العربية والإنجليزية)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/invoice-ai

# نسخ الـ Wheels وتثبيتها
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# إنشاء مستخدم غير جذر للأمان
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
    chown -R appuser:appgroup /srv/invoice-ai

USER appuser

# نسخ كود التطبيق
COPY --chown=appuser:appgroup app ./app

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]