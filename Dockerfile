# =========================================================================
# Dockerfile — Odoo 19 with Invoice Agent extras
#
# Why this approach:
#   BASED ON odoo:19  NOT python:3.12-slim. The official image already ships
#   the Odoo codebase, its entrypoint (which reads HOST/USER/PASSWORD env vars
#   and writes odoo.conf), wkhtmltopdf, the `odoo` user, and /mnt/extra-addons.
#   Rebasing on slim just reimplements all of that poorly.
#
# Layer-caching strategy:
#   1. odoo:19 base       → cached until upstream tag moves
#   2. system packages    → cached until this block changes
#   3. COPY requirements  → cached until deps change (builds separately from source)
#   4. pip install        → cached until requirements.txt changes
#   5. COPY everything    → invalidated by ANY source change (correct — code changes)
# =========================================================================

FROM odoo:19

USER root

# --------------------------------------------------------------------------
# Extra system packages — only what odoo:19 doesn't already ship.
# odoo:19 (Debian bookworm) already has: wkhtmltopdf, postgresql-client,
# node-less, all Python C-ext deps (libxml2, libxslt1, libldap2, etc.).
# We add only what the invoice agent pipeline needs.
# --------------------------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# Python layer — COPY requirements.txt FIRST so Docker layer caching works.
# When only source code changes (not deps), this layer is reused from cache.
# --------------------------------------------------------------------------
# --break-system-packages: odoo:19 ships on Ubuntu Noble which has PEP 668
# enforcement (externally-managed-environment). We are the image builder;
# we know what we're doing.
COPY custom_addons/invoice_agent/requirements.txt /tmp/invoice_agent_requirements.txt
# --ignore-installed: Odoo 19 ships typing_extensions 4.10.0 as a system
# package (deb, not pip). Anthropic pulls typing-extensions>=4.14 and pip
# tries to uninstall the system version, which fails because deb packages
# don't have pip RECORD files. --ignore-installed tells pip to just overlay
# the new version without touching the old package metadata.
RUN if [ -s /tmp/invoice_agent_requirements.txt ]; then \
    pip cache purge 2>/dev/null || true; \
    pip install --break-system-packages --no-cache-dir \
    --ignore-installed \
    --default-timeout=300 --retries=5 \
    --no-input \
    -r /tmp/invoice_agent_requirements.txt; \
    fi \
    && rm -f /tmp/invoice_agent_requirements.txt

# --------------------------------------------------------------------------
# Source code — this layer invalidates on every code change, as it should.
# We copy the full repo so Odoo's addons path can resolve everything.
# custom_addons is bind-mounted at runtime, so we don't COPY it here.
# --------------------------------------------------------------------------
COPY . /opt/odoo
RUN chown -R odoo:odoo /opt/odoo

# Drop back to the odoo user (official image convention)
USER odoo

# The official odoo:19 image exposes 8069 8072 and provides:
#   ENTRYPOINT ["/entrypoint.sh"]
#   CMD ["odoo"]
# We inherit those — no need to repeat.
