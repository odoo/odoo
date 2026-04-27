# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Accounting Reports (post wizard)',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Enable the VAT wizard when posting a tax return journal entry
    """,
    'depends': [
        'l10n_be_reports'
    ],
    'data': [
        'data/res_partner.xml',
        'security/ir.model.access.csv',
        'views/l10n_be_wizard_xml_export_options_views.xml',
        'wizard/vat_pay_wizard.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
