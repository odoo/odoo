# -*- coding: utf-8 -*-
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
        'l10n_multilang',
    ],
    'data': [
        # Chart of Accounts
        'data/account_chart_template_data.xml',
        "data/account.account.template.csv",
        "data/account.group.template.csv",

        # Taxes
        "data/account_tax_group_data.xml",
        "data/account_tax_template_data.xml",

        # Post processing
        "data/account_chart_post_data.xml",
        "data/account_chart_template_try_loading.xml",

        # Data
        "data/l10n_tr.tax_office.csv",

        # Views
        "views/tax_office_views.xml",
        "views/res_partner_views.xml",
        "views/ir_qweb_widget_templates.xml",

        # Security
        "security/ir.model.access.csv",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
    'license': 'LGPL-3',
}
