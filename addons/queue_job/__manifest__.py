# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    "name": "Job Queue",
    "version": "16.0.2.6.8",
    "author": "Camptocamp,ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/queue",
    "license": "LGPL-3",
    "category": "Generic Modules",
    "depends": ["mail", "base_sparse_field", "web"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/queue_job_views.xml",
        "views/queue_job_channel_views.xml",
        "views/queue_job_function_views.xml",
        "wizards/queue_jobs_to_done_views.xml",
        "wizards/queue_jobs_to_cancelled_views.xml",
        "wizards/queue_requeue_job_views.xml",
        "views/queue_job_menus.xml",
        "data/queue_data.xml",
        "data/queue_job_function_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/queue_job/static/src/views/**/*",
        ],
    },
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["guewen"],
    "post_init_hook": "post_init_hook",
    "post_load": "post_load",
}
