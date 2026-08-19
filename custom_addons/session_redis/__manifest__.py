{
    "name": "Redis Session Store",
    "version": "19.0.1.0.0",
    "summary": "Store Odoo HTTP sessions in Redis instead of the filesystem",
    "description": """
        Replaces the default filesystem-backed session store with a Redis
        backend.  Redis sessions are:
        - Shared across all Odoo workers (multi-process safe)
        - Automatically expire after a configurable TTL (default 7 days)
        - Survive container restarts without a shared volume

        Configure via environment variables:
        - ODOO_SESSION_REDIS_URL  -- Redis connection URL
          (default: redis://localhost:6379/0)
        - ODOO_SESSION_REDIS_PREFIX -- key prefix
          (default: 'odoo-session:')

        When ODOO_SESSION_REDIS_URL is not set, the module is a no-op and
        the default file-based session store is used (local dev).
    """,
    "depends": ["base"],
    "data": [],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
