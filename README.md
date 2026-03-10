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
- **GOV Modules:** Specialized `custom_addons/` for government and high-compliance environments.
- **Docker-Ready Stack:** Includes a pre-configured `docker-compose.yml` featuring Odoo, PostgreSQL, and Ollama for local LLM execution.
- **Enhanced Document Processing:** Advanced OCR stack (Tesseract, OCRmyPDF) and LaTeX-based PDF generation.

## Project Structure

- `odoo/`: Core framework code.
- `addons/`: Upstream Odoo modules (treated as vendor code).
- `custom_addons/`: Project-specific modules (`gov_*`, `knowledge/*`, `ai_ml/*`).
- `kodoo_assets/`: Specific branding and configuration assets for the Kodoo distro.

## Getting Started

### Standard Odoo
For a standard installation, follow the [Setup instructions](https://www.odoo.com/documentation/master/administration/install/install.html) from the documentation.

### Kodoo Development
For AI development and Kodoo-specific workflows:
1.  **Read the Guidelines:** Consult `AGENTS.md` for coding standards, testing patterns, and agent interaction protocols.
2.  **Setup Dependencies:** See `GOV_ENV_DEPENDENCIES.md` for system-level requirements (OCR, LaTeX, AI libraries).
3.  **Local Environment:** Use the provided `docker-compose.yml` to spin up the full stack including local AI models.

```bash
pip install -r requirements.txt -r requirements-gov-general.txt
./odoo-bin -c kodoo.conf -d kodoo --addons-path=addons,custom_addons
```

## Security

If you believe you have found a security issue, check our [Responsible Disclosure page](https://www.odoo.com/security-report) for details and get in touch via email.
