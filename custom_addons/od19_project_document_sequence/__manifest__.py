# -*- coding: utf-8 -*-
{
    "name": "Project Document Sequence (OD19)",
    "version": "19.0.1.0.0",
    "summary": "Sale/Service/PM/Job numbering with dept + sales initials + year + sequence",
    "description": """
Adds department-based document sequences for project documents.
Job Number format: J + dept_code + sales_initials + year + sequence
Same format for Sales (JS), Preventive Maintenance (PM), Service (S).
Sales-type projects take their number from the salesperson sequence instead
of a department sequence.
Task Code format: T + dept_code + sales_initials + sequence.
    """,
    "author": "OD19 Custom",
    "category": "Services/Project",
    "license": "LGPL-3",
    "depends": [
        "project",
        "hr",
        "od19_purchase_document_sequence",
        "od19_project_analytic",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "views/hr_department_views.xml",
        "views/res_users_views.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_project_document_sequence/static/description/icon.svg",
}
