# pyright: reportUnusedExpression=false
{
    "name": "Clinic Visit Manager",
    "version": "1.0",
    "summary": "Manage clinic visits and appointments",
    "description": "A module to manage clinic visits, appointments, and patient information.",
    "author": "Soul Software Solutions",
    "website": "https://abis-portfolio.vercel.app/",
    "category": "Healthcare",
    "depends": ["base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "data/clinic_visit_sequence.xml",
        "data/clinic_dashboard_data.xml",
        "views/clinic_visit_views.xml",
        "views/clinic_patient_views.xml",
        "views/clinic_dashboard_views.xml",
    ],      
    "assets": {
        "web.assets_backend": [
            "clinic_visit_manager/static/src/scss/clinic_dashboard.scss",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
