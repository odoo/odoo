# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project - Skills',
    'summary': 'Project skills',
    'description': """
        Search project tasks according to the assignees' skills
    """,
    'category': 'Services/Project',
    'version': '1.0',
    'depends': ['project', 'hr_skills'],
    'auto_install': True,
    'data': [
        'views/project_task_views.xml',
    ],
    'license': 'OEEL-1',
}
