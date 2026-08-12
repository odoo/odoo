# invoice-ai — standalone extraction service (ADR-003)
#
# Runtime deps: Python 3.12 slim + poppler (pdf2image needs pdftoppm) +
# tesseract-ocr (-eng for invoice text; -ara for Arabic bills, matching the
# Odoo image's OCR stack).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# pdf2image shells out to poppler (pdftoppm); pytesseract needs the binary
# and its language data. The same stack the Odoo container carries
# (tesseract-ocr-eng + -ara, poppler-utils).
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/invoice-ai

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8100

# Single process by default; scale with `uvicorn app.main:app --workers N`
# or a container orchestrator replica count. One async process already
# serves many concurrent Claude calls (the whole point of ADR-003).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
