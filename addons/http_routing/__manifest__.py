# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Routing',
    'summary': 'Web Routing',
    'sequence': 9100,
    'category': 'Hidden',
    'description': """
Proposes advanced routing options not available in web or base to keep
base modules simple.
""",
    'data': [
        'views/http_routing_template.xml',
        'views/res_lang_views.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'depends': ['web'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
