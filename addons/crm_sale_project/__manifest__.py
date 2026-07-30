{
    'name': 'CRM - Sales - Project',
    'summary': 'Billable Project Generation from Opportunities',
    'category': 'Sales/CRM',
    'depends': [
        'crm_project',
        'sale_crm',
        'sale_project',
    ],
    'data': [
        'views/project_project_views.xml',
        'wizard/project_template_create_wizard.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
