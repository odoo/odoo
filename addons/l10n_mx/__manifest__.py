# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mexico - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/mexico.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mx'],
    'version': '2.3',
    'author': 'Vauxoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Minimal accounting configuration for Mexico.
============================================

This Chart of account is a minimal proposal to be able to use OoB the
accounting feature of Odoo.

This doesn't pretend be all the localization for MX it is just the minimal
data required to start from 0 in mexican localization.

This modules and its content is updated frequently by openerp-mexico team.

With this module you will have:

 - Minimal chart of account tested in production environments.
 - Minimal chart of taxes, to comply with SAT_ requirements.

.. _SAT: http://www.sat.gob.mx/
    """,
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account.account.tag.csv',
        'data/account_report_diot.xml',
        'data/res_bank_data.xml',
        'views/partner_view.xml',
        'views/res_bank_view.xml',
        'views/account_views.xml',
        'views/account_tax_view.xml',
        "data/l10n_mx_uom.xml",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
    'post_init_hook': '_enable_group_uom_post_init',
}
