# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Croatia - Accounting",
    "description": """
    Croatian Chart of Accounts updated (RRIF ver.2021)
    
    Sources:
    https://www.rrif.hr/dok/preuzimanje/Bilanca-2016.pdf
    https://www.rrif.hr/dok/preuzimanje/RRIF-RP2021.PDF
    https://www.rrif.hr/dok/preuzimanje/RRIF-RP2021-ENG.PDF
    """,
    "version": "13.0",
    "author": "Odoo S.A.",
    'category': 'Accounting/Localizations/Account Charts',

    'depends': [
        'account',
        'base_vat',
        'l10n_multilang',
    ],
    'data': [
        'data/l10n_hr_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',
        'data/account.tax.group.csv',
        'data/account_chart_tag_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/fiscal_templates_data.xml',
        'data/account_fiscal_position_tax_template_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
