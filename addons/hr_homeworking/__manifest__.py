{
    "name": "Remote Work",
    "version": "2.3",
    "category": "Human Resources/Remote Work",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/res_users.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_homeworking/static/src/**/*",
        ],
        "mail.assets_core_common": [
            "hr_homeworking/static/src/work_location_presence.js",
            "hr_homeworking/static/src/components/work_location_presence/**/*",
        ],
        "mail.assets_discuss_core_common": [
            "hr_homeworking/static/src/work_location_presence.js",
            "hr_homeworking/static/src/components/work_location_presence/**/*",
        ],
        "mail.assets_public": [
            "hr_homeworking/static/src/work_location_presence.js",
            "hr_homeworking/static/src/components/work_location_presence/**/*",
        ],
        "im_livechat.assets_embed_core": [
            "hr_homeworking/static/src/work_location_presence.js",
            "hr_homeworking/static/src/components/work_location_presence/**/*",
        ],
        "web.assets_unit_tests": [
            "hr_homeworking/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
