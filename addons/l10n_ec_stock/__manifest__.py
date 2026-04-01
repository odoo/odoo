# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ecuador - Stock',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'description': """Ecuador - Stock""",
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_ec',
        'stock',
    ],
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
