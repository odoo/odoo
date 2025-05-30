# __manifest__.py

{
    'name': 'Hospital Management Custom',
    'version': '1.0',
    'category': 'Healthcare',
    'summary': 'Customizations for Hospital Management Module',
    'description': """
        This module provides custom enhancements and features for hospital management
        in the Odoo system, including custom views, fields, and workflows.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base'],  # Removed 'hospital_management' dependency
    'data': [
        'views/hospital_custom_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
