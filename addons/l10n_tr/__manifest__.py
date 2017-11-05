# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Turkey - Accounting',
    'version': '1.0',
    'category': 'Localization',
    'description': """
Türkiye için Tek düzen hesap planı şablonu Odoo Modülü.
==========================================================

Bu modül kurulduktan sonra, Muhasebe yapılandırma sihirbazı çalışır
    * Sihirbaz sizden hesap planı şablonu, planın kurulacağı şirket, banka hesap
      bilgileriniz, ilgili para birimi gibi bilgiler isteyecek.
    """,
    'author': 'Ahmet Altınışık',
    'maintainer':'https://launchpad.net/~openerp-turkey',
    'website':'https://launchpad.net/openerp-turkey',
    'depends': [
        'account',
    ],
    'data': [
        'data/l10n_tr_chart_data.xml',
        'data/account_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_data.yml',
    ],
}
