# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Slovakia - Income Tax ID',
    'icon': '/account/static/description/l10n.png',
    'countries': ['sk'],
    'category': 'Accounting/Localizations',
    'author': 'IMPLEMENTO s.r.o.',
    'description': """
Slovakia - Income Tax ID
========================
Adds the income tax ID (DIČ) on partners. It identifies Slovak companies on
business documents, and is also required in eInvoicing, where the Peppol EAS
code 0245 designates the DIČ.
    """,
    'depends': [
        'l10n_sk',
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'post_init_hook': '_l10n_sk_dic_post_init',
    'auto_install': True,
    'license': 'LGPL-3',
}
