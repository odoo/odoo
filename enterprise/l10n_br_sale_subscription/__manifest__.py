# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Brazil - Sale Subscription',
    'version': '1.0',
    'description': 'Sale subscription modifications for Brazil',
    'category': 'Localization',
    'depends': [
        'l10n_br',
        'sale_subscription',
    ],
    'data': [
        'views/sale_subscription_portal_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
