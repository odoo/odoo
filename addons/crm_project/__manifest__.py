{
    'name': 'CRM - Project',
    'version': '1.0',
    'summary': 'Project Generation from Opportunities',
    'category': 'Sales/CRM',
    'depends': [
        'project',
        'crm',
    ],
    'data': [
        'views/crm_lead_views.xml',
        'data/ir_actions_server_data.xml',
        'wizard/project_template_create_wizard.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
