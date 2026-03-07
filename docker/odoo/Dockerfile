FROM odoo:19.0

USER root
ARG PYTHON_BIN=python3.12

# GOV runtime dependencies (PDF/LaTeX/OCR) from GOV_ENV_DEPENDENCIES.md.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3.12-venv \
        wkhtmltopdf \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-lang-portuguese \
        lmodern \
        tesseract-ocr \
        tesseract-ocr-por \
        ocrmypdf \
        ghostscript \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kodoo

# Base Odoo dependencies are already present in the upstream odoo image.
# Create a venv that can also see system site-packages (e.g., psycopg2 from base image),
# then install only GOV-specific Python extras in that venv (PEP 668 safe).
COPY requirements-gov-general.txt /opt/kodoo/requirements-gov-general.txt
RUN ${PYTHON_BIN} --version \
    && ${PYTHON_BIN} -m venv --system-site-packages /opt/kodoo-venv \
    && /opt/kodoo-venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/kodoo-venv/bin/pip install --no-cache-dir -r /opt/kodoo/requirements-gov-general.txt
ENV PATH="/opt/kodoo-venv/bin:${PATH}"

USER odoo
