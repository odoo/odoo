# GOV Environment Dependencies

This file defines host dependencies for GOV production environments.

## 1) Python packages (pip)

Install from:

`requirements.txt` (base Odoo) + `requirements-gov-general.txt` (GOV extras)

Command:

```bash
pip install -r requirements.txt -r requirements-gov-general.txt
```

Notes:

- `requirements-gov-general.txt` is the full host bundle.
- `requirements-gov-runtime.txt` contains only the document/runtime extras.
- `requirements-gov-ai.txt` contains the heavyweight AI/embedding extras.

## 2) System binaries (required in host OS)

### PDF, LaTeX and Typst

- `wkhtmltopdf` (HTML -> PDF fallback)
- `pdflatex` (LaTeX -> PDF primary)
- `typst` (optional PDF engine for Typst templates, when available in the target distro)
- TeX packages commonly required by GOV templates:
  - `texlive-latex-base`
  - `texlive-latex-recommended`
  - `texlive-latex-extra`
  - `texlive-fonts-recommended`
  - `texlive-lang-portuguese`
  - `lmodern`

### Document conversion and file detection

- `pandoc` (recommended for Markdown and text conversion pipelines)
- `libmagic1` (recommended for MIME/file-type detection used by Python tooling)

### OCR stack (recommended for scanned documents)

- `tesseract-ocr`
- `tesseract-ocr-por`
- `ocrmypdf`
- `ghostscript`
- `poppler-utils`

## 3) Ubuntu/Debian example

```bash
sudo apt-get update
sudo apt-get install -y \
  wkhtmltopdf \
  texlive-latex-base texlive-latex-recommended texlive-latex-extra \
  texlive-fonts-recommended texlive-lang-portuguese lmodern \
  pandoc libmagic1 \
  tesseract-ocr tesseract-ocr-por \
  ocrmypdf ghostscript poppler-utils
```

If your distro provides `typst`, add it as well.

## 4) Windows host example (Chocolatey)

```powershell
choco install -y wkhtmltopdf miktex tesseract ghostscript poppler
```

After installing MiKTeX, ensure `pdflatex.exe` is available in `PATH`.

## 5) GOV AI config params (database)

Set these for Hugging Face / LangChain embeddings:

- `gov_ai_ml.embedding_provider` = `huggingface_langchain` or `local_tfidf`
- `gov_ai_ml.embedding_model_name` = e.g. `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `gov_ai_ml.huggingface_api_key` = your HF token (optional for some local models)

Lexoid parser params (optional):

- `gov_ai_ml.lexoid_endpoint`
- `gov_ai_ml.lexoid_api_key`
- `gov_ai_ml.lexoid_timeout_seconds`

## 6) lnav mode (alternative startup)

- `lnav` is available on this host and can display the live Odoo log.
- Run `scripts\\start-with-lnav.ps1` to launch Odoo with `logs/odoo-lnav.log` and open `lnav` in a separate window.
  * Edit the `$Config`/`$Db` parameters at the top of the script if you need another configuration or database name.

## 7) Docker environment (this repository)

The repository now separates the images clearly:

- Base image: `docker/odoo/Dockerfile`
- Public-sector runtime image: `docker/odoo/Dockerfile.public-sector`
- Default stack: `docker-compose.yml` uses the public-sector runtime image
- Plain Odoo override: `docker-compose.base.yml`
- The default public-sector image installs only runtime/document extras; AI extras are opt-in.

Build and start with the public-sector runtime:

```bash
docker compose build odoo
docker compose up -d
```

Build and start without public-sector runtime extras:

```bash
docker compose -f docker-compose.yml -f docker-compose.base.yml build odoo
docker compose -f docker-compose.yml -f docker-compose.base.yml up -d
```

Optional extra packages for the public-sector image can be injected at build time:

```bash
PUBLIC_SECTOR_EXTRA_APT_PACKAGES="typst" \
PUBLIC_SECTOR_EXTRA_PIP_PACKAGES="" \
docker compose build odoo
```

If you also want the heavyweight AI/embedding stack inside the public-sector container:

```bash
PUBLIC_SECTOR_INSTALL_AI_EXTRAS=1 docker compose build odoo
```
