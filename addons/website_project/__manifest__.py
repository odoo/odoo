{
    "name": "Online Task Submission",
    "version": "1.1",
    "category": "Website/Website",
    "summary": "Add a task suggestion form to your website",
    "description": """
Generate tasks in Project app from a form published on your website. This module requires the use of the *Form Builder* module in order to build the form.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website",
        "project",
    ],
    "data": [
        "data/website_project_data.xml",
        "views/project_portal_project_task_template.xml",
        "views/project_portal_project_project_template.xml",
    ],
    "assets": {
        "website.website_builder_assets": [
            "website_project/static/src/js/website_project_editor.js",
        ],
        "project.webclient": [
            "website/static/src/js/utils.js",
            "web/static/src/components/autocomplete/*",
            "website/static/src/components/autocomplete_with_pages/*",
        ],
    },
    "auto_install": True,
}
