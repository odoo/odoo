# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Report Engine: Paper Muncher",
    'summary': "Paper Muncher Engine",
    'version': '1.0',
    'description': """
This module is the implementation of the odoo's
in house rendering engine called Paper Muncher.

learn more about it here:
https://odoo.github.io/paper-muncher/
    """,
    'depends': [
        'base_setup',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'category': 'Hidden/Tools',
    'post_init_hook': 'post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
