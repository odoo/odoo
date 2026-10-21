# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Vietnam - E-invoicing (eHoaDon)',
    'icon': '/account/static/description/l10n.png',
    'countries': ['vn'],
    'version': '1.0',
    'author': 'BizStore Group',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/vietnam.html',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'E-invoicing using eHoaDon Online by BizStore',
    'description': """
Vietnam - E-invoicing
=====================
Using eHoaDon Online by BizStore.

**Credits:**
    - BizStore Group (https://ehoadon.online)
""",
    'depends': [
        'account',
        'l10n_vn',
    ],
    'data': [
        'security/ehoadon_security.xml',
        'security/ir.access.csv',
        'views/ehoadon_config_views.xml',
        'views/ehoadon_template_views.xml',
        'views/ehoadon_menu.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
