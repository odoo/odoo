{
    "name": "Project Git",
    "summary": "Minimal git review proof of concept on project tasks",
    "version": "19.0.1.4.0",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["project", "mail", "web"],
    "data": [
        "views/project_task_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_git/static/src/js/project_git_diff_field.js",
            "project_git/static/src/xml/project_git_diff_field.xml",
            "project_git/static/src/scss/project_git_diff_field.scss",
        ],
    },
    "installable": True,
    "application": False,
}
