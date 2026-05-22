# Tech Stack

**Source:** setup.py, requirements.txt, odoo/release.py, ruff.toml, setup.cfg

| Layer | Technology | Version/Notes |
|-------|-----------|--------------|
| **Framework** | Odoo | 19.0 (FINAL) |
| **Language** | Python | 3.10 – 3.14 (MIN_PY_VERSION=3.10, MAX_PY_VERSION=3.14) |
| **Database** | PostgreSQL | >= 13 (MIN_PG_VERSION=13), psycopg2 adapter |
| **HTTP Server** | Werkzeug | 2.0.2 – 3.0.1 (version varies by Python) |
| **Web Framework** | Jinja2 | 3.0.3 – 3.1.2 (templating) |
| **ORM** | Odoo ORM | Built-in; models/orm modules |
| **Async Runtime** | gevent + greenlet | Async worker pools (non-Windows) |
| **CLI** | odoo-cli | 20 subcommands in odoo/cli/ |
| **Linter** | Ruff | 0.15.0+ (config: ruff.toml) |
| **Code Style** | Ruff + Flake8 | 45+ rules (E, F, UP, TRY, RUF, etc.) |
| **Testing** | freezegun | Time mocking (1.1.0 – 1.5.1) |
| **Documentation** | docutils + Sphinx | RST directives, @versionadded/@deprecated |
| **XML Schema** | RelaxNG | import_xml.rng for manifest validation |
| **Frontend** | OWL Components | JavaScript/XML (no JS in core; addons may include) |
| **Build** | setuptools | namespace packages, find_namespace_packages() |
| **Security** | cryptography + pyOpenSSL | TLS, encryption (3.4.8 – 42.0.8) |

## Key Dependencies

| Category | Packages |
|----------|----------|
| **Data Processing** | openpyxl, xlrd, xlsxwriter, xlwt (Excel); PyPDF/PyPDF2 (PDF); reportlab (report generation) |
| **Cryptography** | cryptography, pyopenssl, passlib (password hashing), qrcode, zeep (SOAP) |
| **Imaging** | Pillow (image processing), libsass (CSS preprocessing) |
| **Serialization** | cbor2, lxml, vobject (iCalendar), ofxparse (OFX banking) |
| **Localization** | Babel (i18n), polib (PO file handling), num2words (number translation) |
| **System** | psutil (process monitoring), pyserial (hardware), pyusb (USB), geoip2 (geo lookup) |
| **HTTP** | requests, urllib3 (HTTP client), Werkzeug (WSGI server) |
| **Utilities** | python-dateutil, pytz (timezone), chardet (encoding detection), idna |
| **Optional** | python-ldap (directory integration, Linux only) |

## Supported Platforms

- **Linux/macOS:** Full support (gevent enabled)
- **Windows:** Limited support (gevent unavailable, pypiwin32 fallback)

## Build & Distribution

- **License:** LGPL-3
- **Package Format:** Namespace packages (odoo.* namespace)
- **Entry Point:** setup/odoo (CLI entry script)
- **Python Requires:** >= 3.10 (enforced in setup.py)

## Development Requirements

- **Testing:** freezegun (time mocking)
- **Linting:** Ruff (config in ruff.toml)
- **Doc Building:** Sphinx-compatible RST format
