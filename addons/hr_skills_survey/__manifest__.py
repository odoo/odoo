{
    "name": "Skills Certification",
    "version": "1.1",
    "category": "Human Resources/Employees",
    "summary": "Add certification to resume of your employees",
    "description": """
Certification and Skills for HR
===============================

This module adds certification to resume for employees.
        """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr_skills",
        "survey",
    ],
    "data": [
        "data/hr_resume_data.xml",
        "views/hr_resume_line_views.xml",
        "views/survey_survey_views.xml",
    ],
    "demo": [
        "demo/hr_resume_demo.xml",
    ],
    "auto_install": True,
}
