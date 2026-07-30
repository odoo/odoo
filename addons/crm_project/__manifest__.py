{
    'name': 'CRM - Project',
    'summary': 'Project Generation from Leads',
    'description': """
Create a project, optionally from a project template, directly from a lead or an
opportunity, and follow the projects and tasks generated for it from the lead.
""",
    'category': 'Sales/CRM',
    'depends': [
        'crm',
        'project',
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
