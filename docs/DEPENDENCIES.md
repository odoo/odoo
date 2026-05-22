# Dependencies

**Source:** requirements.txt (103 pinned packages), setup.py, Ubuntu 24.04 / Debian 12 compatibility

## System Dependencies

| Dependency | Purpose | Required | Version |
|-----------|---------|----------|---------|
| **PostgreSQL** | Primary database | YES | >= 13 (MIN_PG_VERSION=13) |
| **Python** | Runtime | YES | 3.10 – 3.14 |
| **libsass** | CSS preprocessing | YES | 0.20.1 – 0.22.0 |
| **libxml2, libxslt** | XML/XSLT processing | YES | (system packages) |
| **libjpeg, zlib** | Image processing (Pillow) | YES | (system packages) |
| **OpenSSL** | TLS/encryption | YES | (system packages) |

## Python Dependencies by Category

### HTTP & WSGI
| Package | Version | Purpose |
|---------|---------|---------|
| Werkzeug | 2.0.2 – 3.0.1 | WSGI application server |
| requests | 2.25.1 – 2.31.0 | HTTP client library |
| urllib3 | 1.26.5 – 2.0.7 | HTTP connection pooling |
| Jinja2 | 3.0.3 – 3.1.2 | Template engine |
| MarkupSafe | 2.0.1 – 2.1.5 | Safe template escaping |

### Database & ORM
| Package | Version | Purpose |
|---------|---------|---------|
| psycopg2 | 2.9.2 – 2.9.10 | PostgreSQL adapter (Python 3.10+) |
| sqlalchemy | (optional via tools) | SQL expression language |
| lxml | 4.8.0 – 5.2.1 | XML/HTML parsing; depends on libxml2 |
| lxml-html-clean | (unpinned, 3.12+) | HTML sanitization (separated in lxml 5.x) |

### Async & Concurrency
| Package | Version | Purpose |
|---------|---------|---------|
| gevent | 21.8.0 – 24.11.1 | Async I/O via greenlets (Linux/macOS only) |
| greenlet | 1.1.2 – 3.3.2 | Lightweight concurrency primitives |

### Cryptography & Security
| Package | Version | Purpose |
|---------|---------|---------|
| cryptography | 3.4.8 – 42.0.8 | Encryption, key derivation, certificate handling |
| pyOpenSSL | 21.0.0 – 24.1.0 | TLS/SSL bindings |
| passlib | 1.7.4 | Password hashing (bcrypt, argon2, scrypt) |
| pyasn1 | (via cryptography) | ASN.1 encoding/decoding |
| asn1crypto | 1.4.0 – 1.5.1 | ASN.1 (certificates, keys) |
| idna | 2.10 – 3.6 | Internationalized domain names |
| chardet | 4.0.0 – 5.2.0 | Character encoding detection |

### Data Processing
| Package | Version | Purpose |
|---------|---------|---------|
| openpyxl | 3.0.9 – 3.1.2 | Read/write Excel (.xlsx) |
| xlrd | 1.2.0 – 2.0.1 | Read Excel (.xls) |
| XlsxWriter | 3.0.2 – 3.1.9 | Write Excel (.xlsx) |
| xlwt | 1.3.0 | Write Excel (.xls) |
| PyPDF2 / PyPDF | 1.26.0 – 5.4.0 | PDF manipulation (text extraction, merging) |
| reportlab | 3.6.8 – 4.1.0 | PDF generation (invoices, reports) |
| cbor2 | 5.4.2 – 5.6.2 | CBOR serialization (binary data) |
| ofxparse | 0.21 | OFX banking format parsing |

### Localization & i18n
| Package | Version | Purpose |
|---------|---------|---------|
| Babel | 2.9.1 – 2.17.0 | Internationalization (i18n) toolkit |
| polib | 1.1.1 | .PO/.POT (gettext) file handling |
| num2words | 0.5.10 – 0.5.13 | Convert numbers to words (multilingual) |
| pytz | (unpinned) | Timezone database |

### Imaging & Documents
| Package | Version | Purpose |
|---------|---------|---------|
| Pillow | 9.0.1 – 12.1.1 | Image processing (JPEG, PNG, GIF) |
| libsass | 0.20.1 – 0.22.0 | CSS preprocessing (SASS to CSS) |
| python-magic | 0.4.24 – 0.4.27 | File type detection (MIME) (Linux/macOS) |

### Barcodes, QR, Geo
| Package | Version | Purpose |
|---------|---------|---------|
| qrcode | 7.3.1 – 7.4.2 | QR code generation |
| geoip2 | 2.9.0 | GeoIP database lookups |
| pyusb | 1.2.1 | USB device access (hardware integration) |
| pyserial | 3.5 | Serial port communication (IoT) |

### XML & Web Services
| Package | Version | Purpose |
|---------|---------|---------|
| zeep | 4.1.0 – 4.3.1 | SOAP/WSDL client |
| vobject | 0.9.6.1 – 0.9.9 | iCalendar (vCard/ics) parsing |
| docutils | 0.17 – 0.20.1 | RST documentation parsing |

### Utilities & Monitoring
| Package | Version | Purpose |
|---------|---------|---------|
| psutil | 5.9.0 – 5.9.8 | Process monitoring (CPU, memory, disk) |
| python-dateutil | 2.8.1 – 2.8.2 | Date/time utilities (fuzzy parsing, tz) |
| rjsmin | 1.1.0 – 1.2.0 | JavaScript minification |

### Optional Dependencies
| Package | Purpose | Condition |
|---------|---------|-----------|
| python-ldap | LDAP/directory integration | Windows: unavailable; Linux/macOS: optional |
| pypiwin32 | Windows-specific APIs | Windows only |
| rl-renderPM | Windows PDF rendering | Windows + Python 3.12+ |

## Testing Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| freezegun | 1.1.0 – 1.5.1 | Mock time.now() for deterministic testing |

## Development & Tooling

| Tool | Config File | Purpose |
|------|------------|---------|
| Ruff | ruff.toml | Linting (45+ rules: E, F, UP, TRY, RUF, etc.) |
| Flake8 | setup.cfg | Code style (deprecated, superseded by Ruff) |
| setuptools | setup.py | Package build, namespace packages |

## Dependency Resolution Strategy

**Requirements.txt Format:**
- Pinned to Ubuntu 24.04 & Debian 12 package versions
- Multi-version entries for Python 3.10 → 3.13/3.14 upgrades
- Example: Babel (2.9.1 for 3.10, 2.10.3 for 3.11+, 2.17.0 for 3.13+)
- Non-Windows platform markers (e.g., `sys_platform != 'win32'` for gevent)

**Compatibility Guarantees:**
- MIN_PY_VERSION = 3.10 (setup.py enforced)
- MIN_PG_VERSION = 13 (setup.py)
- MAX_PY_VERSION = 3.14 (future-proofing)
- Ubuntu 24.04 LTS + Debian 12 baseline

## Installation

```bash
# Production
pip install -r requirements.txt

# Development (includes test packages)
pip install -r requirements.txt freezegun

# From source
python setup.py install
```

## External Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| **PostgreSQL** | Data persistence | Primary RDBMS |
| **SMTP** | Email dispatch | Via python-smtplib (stdlib) |
| **LDAP** | User authentication | Optional (python-ldap) |
| **GeoIP Database** | Geolocation | Via MaxMind GeoIP2 |
| **SOAP Services** | EDI, integrations | Via zeep |

## Notes

- **No Node.js/npm:** OWL (frontend framework) is embedded; no separate JS build step required
- **No Docker:** Debian packaging preferred; Docker is community-contributed
- **No ORM Lock-in:** Odoo ORM is proprietary; no SQLAlchemy/Alembic hard dependency
- **Platform Variance:** gevent/greenlet unavailable on Windows; fallback to standard threading
- **Upgrade Path:** requirements.txt explicitly manages multi-version transitions (3.10 → 3.14)
