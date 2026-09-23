{
    "name": "Project - SMS",
    "version": "1.1",
    "category": "Services/Project",
    "summary": "Send text messages when project/task stage move",
    "description": "Send text messages when project/task stage move",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "project",
        "sms",
    ],
    "data": [
        "views/project_phase_views.xml",
        "views/project_workflow_step_views.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "security/ir.access.csv",
    ],
    "auto_install": True,
}
