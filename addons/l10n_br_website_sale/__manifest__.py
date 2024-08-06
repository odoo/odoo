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
        'data/ir_model_fields.xml',

        'views/portal.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_br_website_sale/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_br_website_sale/static/tests/**/*',
        ]
    },
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_l10n_br_website_sale_post_init_hook',
    'license': 'LGPL-3',
}
