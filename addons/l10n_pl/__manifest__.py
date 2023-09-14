# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Poland - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pl'],
    'version': '2.0',
    'author': 'Odoo S.A., Grzegorz Grzelak (OpenGLOBE) (http://www.openglobe.pl)',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the module to manage the accounting chart and taxes for Poland in Odoo.
==================================================================================

To jest moduł do tworzenia wzorcowego planu kont, podatków, obszarów podatkowych i
rejestrów podatkowych. Moduł ustawia też konta do kupna i sprzedaży towarów
zakładając, że wszystkie towary są w obrocie hurtowym.

Niniejszy moduł jest przeznaczony dla odoo 8.0.
Wewnętrzny numer wersji OpenGLOBE 1.02
    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_pl.l10n_pl_tax_office.csv',
        'data/res.country.state.csv',
        'data/account.account.tag.csv',
        'data/account_tax_report_data.xml',
        'views/account_move_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_preserve_tag_on_taxes',
    'license': 'LGPL-3',
}
