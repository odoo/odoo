# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Netherlands - Accounting Reports (post wizard)',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Enable the VAT wizard when posting a tax return journal entry
    """,
    'depends': ['l10n_nl_reports'],
    'data': [
        'data/res_partner.xml',
        'security/ir.model.access.csv',
        'wizard/vat_pay_wizard.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
