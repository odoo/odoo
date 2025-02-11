# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Brazil - Website Sale',
    'version': '1.0',
    'description': 'Bridge Website Sale for Brazil',
    'category': 'Localization',
    'depends': [
        'l10n_br',
        'website_sale',
    ],
    'data': [
        'views/portal.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
