{
    'name': 'CRM - Project',
    'summary': 'Project Generation from Opportunities',
    'category': 'Sales/CRM',
    'depends': [
        'sale_project',
        'crm',
    ],
    'data': [
        'data/ir_actions_server_data.xml',
        'views/crm_lead_views.xml',
        'views/project_project_views.xml',
        'wizard/project_template_create_wizard.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
