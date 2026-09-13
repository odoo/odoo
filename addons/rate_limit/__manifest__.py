{
    "name": "Rate Limiting",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Token buckets shared across workers and an in-process sliding-window limiter",
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/ir_cron.xml",
        "views/rate_limit_bucket_views.xml",
        "views/rate_limit_menus.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
