# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Romanian SAF-T Export',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ro'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': '''
This module enables generating the D.406 declaration from within Odoo.
The D.406 declaration is an XML file in the SAF-T format which Romanian companies
must submit monthly or quarterly, depending on their tax reporting period.
    ''',
    'depends': [
        'l10n_ro', 'account_saft',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/saft_report.xml',
        'data/l10n_ro_saft.tax.type.csv',
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': ['l10n_ro', 'account_saft'],
    'post_init_hook': '_update_saft_fields_on_taxes',
}
