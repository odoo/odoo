# GOV Environment Dependencies

This file defines host dependencies for GOV production environments.

## 1) Python packages (pip)

Install from:

`requirements.txt` (base Odoo) + `requirements-gov-general.txt` (GOV extras)

Command:

```bash
pip install -r requirements.txt -r requirements-gov-general.txt
```

## 2) System binaries (required in host OS)

### PDF and LaTeX

- `wkhtmltopdf` (HTML -> PDF fallback)
- `pdflatex` (LaTeX -> PDF primary)
- TeX packages commonly required by GOV templates:
  - `texlive-latex-base`
  - `texlive-latex-recommended`
  - `texlive-latex-extra`
  - `texlive-fonts-recommended`
  - `texlive-lang-portuguese`
  - `lmodern`

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
  tesseract-ocr tesseract-ocr-por \
  ocrmypdf ghostscript poppler-utils
```

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
