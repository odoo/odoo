{
    'name': 'Project Duplicate',
    'author': 'Odoo S.A.',
    'summary': 'Detect duplicate project tasks using pgvector and fastembed',
    'category': 'Services/Project',
    'depends': ['project'],
    'data': [
        'security/ir.access.csv',
        'wizard/project_task_duplicate_wizard_views.xml',
        'views/project_task_views.xml',
        'data/ir_cron.xml',
    ],
    'pre_init_hook': '_pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
