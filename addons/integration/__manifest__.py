{
    "name": "Integration",
    "version": "19.0.1.32.0",
    "category": "Hidden",
    "sequence": 5,
    "summary": "Inbound and outbound API transport with auth, rate limiting, retry and logging",
    "description": """
Integration
===========

Transport layer for inbound and outbound API traffic.

Models
------
* ``mixin.integration.receiver`` -- webhook and IoT receivers
* ``integration.service`` -- REST and external service callers
* ``integration.exchange`` -- event log for both directions
* ``integration.response.cache`` -- outbound response cache
* ``mixin.integration.channel`` -- behaviour shared by both endpoint models

Requirements
------------
* ``ODOO_API_ENCRYPTION_KEY`` in the server's environment before a secret is
  stored: every credential is encrypted with it. The module, its data and its
  demo install without it -- their credentials exist unprovisioned until a
  secret is entered.

Authentication
--------------
* Bearer token
* HMAC signature, SHA-256 and SHA-512, constant-time comparison
* OAuth 2.0, outbound
* IP whitelist, inbound
* Timestamp verification against replay

Traffic control
---------------
* Token-bucket rate limiting, database-backed, per endpoint
* Retry with exponential backoff
* Response caching
* Session pooling
* Async queue for inbound events
* Health checks for outbound services

Logging
-------
* Direction, timing and error category per event
* Secret redaction
* Configurable retention

Secrets are encrypted by ``credential``. Record rules scope every
model by company.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "credential",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_config_parameter_data.xml",
        "data/ir_cron_data.xml",
        "data/api_service_data.xml",
        "views/integration_exchange_views.xml",
        "views/inbound_access_log_views.xml",
        "views/integration_service.xml",
        "views/integration_connection_views.xml",
        "views/integration_receiver_views.xml",
        "views/ir_actions_server_views.xml",
        "views/response_cache_views.xml",
        "views/api_credential_views.xml",
        "views/api_credential_access_log_views.xml",
        "wizards/res_config_settings_views.xml",
        "views/integration_menu.xml",
    ],
    "demo": [
        "demo/integration_demo_data.xml",
        "demo/api_demo_data.xml",
    ],
    "application": True,
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
}
