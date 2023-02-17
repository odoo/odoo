# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Turkey - Accounting',
    'version': '1.0',
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
