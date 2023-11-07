# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Turkey - Accounting',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['tr'],
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Türkiye için Tek düzen hesap planı şablonu Odoo Modülü.
==========================================================

Bu modül kurulduktan sonra, Muhasebe yapılandırma sihirbazı çalışır
    * Sihirbaz sizden hesap planı şablonu, planın kurulacağı şirket, banka hesap
      bilgileriniz, ilgili para birimi gibi bilgiler isteyecek.
    """,
    'author': 'Odoo',
    'depends': [
        'account',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
