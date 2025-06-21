# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Argentina - Payment Withholdings',
    'version': "1.0",
    'description': """Allows to register withholdings during the payment of an invoice.""",
    'author': 'ADHOC SA',
    'countries': ['ar'],
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_ar',
        'l10n_latam_check',
    ],
    'data': [
        'views/account_tax_views.xml',
        'views/account_payment_view.xml',
        'views/report_payment_receipt_templates.xml',
        'views/res_config_settings.xml',
        'wizards/account_payment_register_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'post_init_hook': '_l10n_ar_withholding_post_init',
    'license': 'LGPL-3',
}
