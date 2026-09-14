{
    "name": "Skills Management",
    "version": "1.3",
    "category": "Human Resources/Employees",
    "sequence": 270,
    "summary": "Manage skills, knowledge and resume of your employees",
    "description": """
Skills and Resume for HR
========================

This module introduces skills and resume management for employees.
        """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/hr_skills_security.xml",
        "views/hr_views.xml",
        "views/hr_job_views.xml",
        "views/hr_job_skill_views.xml",
        "data/hr_resume_data.xml",
        "data/hr_skill_data.xml",
        "data/ir_cron_data.xml",
        "data/mail_activity_type_data.xml",
        "data/report_paperformat.xml",
        "reports/hr_employee_certification_report_views.xml",
        "reports/hr_employee_skill_history_report_views.xml",
        "reports/hr_employee_skill_report_views.xml",
        "reports/hr_employee_cv_report.xml",
        "views/hr_department_views.xml",
        "views/hr_employee_cv_templates.xml",
        "wizards/hr_employee_cv_wizard_views.xml",
        "views/hr_skills_menus.xml",
    ],
    "demo": [
        "demo/hr_skill_demo.xml",
        "demo/hr_resume_demo.xml",
        "demo/hr_job_skill_demo.xml",
        "demo/hr.job.skill.csv",
        "demo/hr.employee.skill.csv",
        "demo/hr_employee_skill_demo.xml",
        "demo/hr.resume.line.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_skills/static/src/fields/skills_one2many/*",
            "hr_skills/static/src/fields/**/*",
            "hr_skills/static/src/scss/*.scss",
            "hr_skills/static/src/views/**/*",
            "hr_skills/static/src/components/**/*",
        ],
        "web.assets_unit_tests": [
            "hr_skills/static/tests/**/*",
            (
                "remove",
                "hr_skills/static/tests/tours/**/*",
            ),
        ],
        "web.assets_tests": [
            "hr_skills/static/tests/tours/**/*",
        ],
        "web.report_assets_pdf": [
            "/hr_skills/static/src/scss/report_employee_cv.scss",
        ],
    },
    "application": True,
    "auto_install": True,
}
