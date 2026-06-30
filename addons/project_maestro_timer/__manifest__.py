# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Cronômetro de Tarefas (Maestro)',
    'version': '1.0',
    'category': 'Project',
    'summary': 'Cronômetro estilo Bitrix nas tarefas e relatório de eficácia por semana/mês/ano',
    'depends': ['project', 'hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_task_views.xml',
        'views/project_timer_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_maestro_timer/static/src/components/task_timer/task_timer.js',
            'project_maestro_timer/static/src/components/task_timer/task_timer.xml',
            'project_maestro_timer/static/src/components/task_timer/task_timer.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
