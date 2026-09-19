{
    "name": "Credential Vault",
    "version": "19.0.1.19.1",
    "category": "Hidden",
    "sequence": 5,
    "summary": "Foundation module for secure credential management across all external integrations",
    "description": """
Credential Vault
================

Foundation module providing secure credential management infrastructure for ALL external service integrations.

Key Features
------------
**Universal Credential Storage:**
* Encrypted credential storage using Fernet (AES-128)
* Environment variable key management (ODOO_API_ENCRYPTION_KEY)
* Support for multiple credential types (API Key, OAuth, AWS IAM, etc.)
* Credential validation framework

X.509 material is deliberately out of scope: certificates and private keys
belong to ``certificate.certificate`` / ``certificate.key`` in the
``certificate`` module, which own the parsing, the cert/key compatibility
constraint and the signing API. That module holds them encrypted at rest with
the same mixin used here, with no separate install.

**Multi-Tenancy:**
* Company-scoped credentials with automatic isolation
* Record rules enforce company boundaries
* Cost segregation per company

**Security:**
* Field-level encryption (Fernet symmetric encryption)
* Encryption key stored in environment variable (NOT database)
* Audit logging for credential access
* Health monitoring and validation

**Developer Experience:**
* Simple mixin pattern for credential models
* Pluggable validation framework
* Comprehensive error messages
* Full test coverage

Usage
-----
Other modules build on this module in two ways:

* Reference ``credential.credential`` records (or extend the model via
  ``_inherit``) to store their secrets encrypted — see ``integration``, which
  absorbed both ``api_communication`` and ``api_gateway``.
Rate limiters live in ``rate_limit``. The inbound gate, its access log and
the signature-verification helpers live in ``integration``, as do the
outbound session cache; the device connection manager lives in ``remote``.

Requires the ``ODOO_API_ENCRYPTION_KEY`` environment variable (a Fernet key);
old keys stay readable through ``ODOO_API_ENCRYPTION_KEY_V<n>`` during
rotation.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mixin_encryption",
        "rate_limit",
    ],
    "data": [
        "security/credential_security.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/credential_category_data.xml",
        "data/credential_category_field_data.xml",
        "data/ir_cron.xml",
        "views/credential_credential_views.xml",
        "views/credential_category_views.xml",
        "views/credential_access_log_views.xml",
        "views/credential_use_views.xml",
        "views/credential_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "credential/static/src/fields/credential_secret_fields.js",
            "credential/static/src/fields/credential_secret_fields.xml",
        ],
    },
    "pre_init_hook": "pre_init_hook",
}
