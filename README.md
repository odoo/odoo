# Odoo (Kodoo Distribution)

[![Build Status](https://runbot.odoo.com/runbot/badge/flat/1/master.svg)](https://runbot.odoo.com/runbot)
[![Tech Doc](https://img.shields.io/badge/master-docs-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/documentation/master)
[![Help](https://img.shields.io/badge/master-help-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](https://img.shields.io/badge/master-nightly-875A7B.svg?style=flat&colorA=8F8F8F)](https://nightly.odoo.com/)

Odoo is a suite of web-based open-source business apps.

**Kodoo** is a specialized distribution of Odoo tailored for advanced integrations, government-grade workflows (GOV), and AI-centric development. It serves as a comprehensive framework for building intelligent ERP solutions.

## Kodoo: AI-Ready ERP Distribution

Kodoo extends the standard Odoo core with a focus on modern AI/ML capabilities and modularity:

- **AI & LLM Integration:** Built-in support for Hugging Face, LangChain, and vector embeddings.
- **Agent-First Design:** Optimized for AI agents to interact with the ERP via structured APIs and clear module boundaries (see `AGENTS.md`).
- **Public-Sector Suite:** Specialized `custom_addons/public_sector/` modules for government and high-compliance environments.
- **Docker-Ready Stack:** Includes a pre-configured `docker-compose.yml` featuring Odoo, PostgreSQL, and Ollama for local LLM execution.
- **Enhanced Document Processing:** Advanced OCR stack (Tesseract, OCRmyPDF) and LaTeX-based PDF generation.
- **Dedicated Public-Sector Runtime:** The Docker stack can run with a public-sector-focused Odoo image that isolates LaTeX, OCR, Typst-ready, and document-ingest dependencies.
- **Optional AI Extras:** Heavy embedding/ML dependencies can be enabled only when needed, instead of inflating the default public-sector container.

## Project Structure

- `odoo/`: Core framework code.
- `addons/`: Upstream Odoo modules (treated as vendor code).
- `custom_addons/`: Project-specific modules, including the public-sector suite in `public_sector/gov_*`, `knowledge/*`, and other local bundles.
- `kodoo_assets/`: Specific branding and configuration assets for the Kodoo distro.

## Getting Started

### Standard Odoo
For a standard installation, follow the [Setup instructions](https://www.odoo.com/documentation/master/administration/install/install.html) from the documentation.

### Kodoo Development
For AI development and Kodoo-specific workflows:
1.  **Read the Guidelines:** Consult `AGENTS.md` for coding standards, testing patterns, and agent interaction protocols.
2.  **Setup Dependencies:** See `GOV_ENV_DEPENDENCIES.md` for system-level requirements (OCR, LaTeX, AI libraries).
3.  **Choose the runtime mode that matches the job:**
    - `make dev` for native Odoo with database manager over Docker PostgreSQL
    - `make dev-safe` for native Odoo with database manager over local PostgreSQL
    - Docker for the stable/public-like stack refreshed with `make refresh-safe`

```bash
python -m pip install -r requirements.txt -r requirements-gov-runtime.txt
make dev-safe
```

Optional AI extras for native/local tests:

```bash
python -m pip install -r requirements-gov-ai.txt
```

For the stable Docker stack:

```bash
docker compose build odoo
docker compose up -d
make refresh-safe
```

To include the optional AI/embedding stack inside the public-sector image:

```bash
PUBLIC_SECTOR_INSTALL_AI_EXTRAS=1 docker compose build odoo
```

Recommended workflow split:

- `make dev`: native Odoo, database manager, shared Docker PostgreSQL data
- `make dev-safe`: native Odoo, database manager, isolated local PostgreSQL data
- `make dev-host-up`: native Odoo, database manager, isolated local PostgreSQL data
- Docker: stable/public-like runtime

If you want a plain Odoo image without the public-sector runtime extras:

```bash
docker compose -f docker-compose.yml -f docker-compose.base.yml build odoo
docker compose -f docker-compose.yml -f docker-compose.base.yml up -d
```

## Security

If you believe you have found a security issue, check our [Responsible Disclosure page](https://www.odoo.com/security-report) for details and get in touch via email.
