{
    'name': 'Training Module',
    'version': '1.0',
    'category': 'Training',
    'summary': 'Custom module for Odoo training exercises',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_partner_views.xml',
        'report/training_record_templates.xml',
        'report/training_record_report.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
