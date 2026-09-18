__all__ = [
    "CACHES_BY_KEY",
    "CRON_TRIGGER_CHANNEL",
    "JOB_QUEUE_CHANNEL",
    "REGISTRY_CACHES",
]

CRON_TRIGGER_CHANNEL = "cron_trigger"

JOB_QUEUE_CHANNEL = "job_queue"


REGISTRY_CACHES = {
    "default": 8192,
    "assets": 512,
    "assets.links": 8192,
    "assets.files": 8192,
    "stable": 1024,
    "templates": 1024,
    "templates.mail": 512,
    "routing": 1024,
    "routing.rewrites": 8192,
    "templates.cached_values": 2048,
    "groups": 64,
    "product_variants": 8192,
    "actions": 256,
    "xmlid": 8192,
    "mail": 64,
}

CACHES_BY_KEY = {
    "default": (
        "default",
        "templates.cached_values",
        "product_variants",
        "xmlid",
        "mail",
    ),
    "assets": ("assets", "assets.links", "assets.files", "templates.cached_values"),
    "stable": (
        "stable",
        "default",
        "templates.cached_values",
        "product_variants",
        "xmlid",
        "mail",
    ),
    "templates": ("templates", "templates.mail", "templates.cached_values"),
    "routing": ("routing", "routing.rewrites", "templates.cached_values"),
    "groups": (
        "groups",
        "templates",
        "templates.mail",
        "templates.cached_values",
    ),
    "product_variants": ("product_variants",),
    "actions": ("actions",),
    "xmlid": ("xmlid",),
    "mail": ("mail",),
}
