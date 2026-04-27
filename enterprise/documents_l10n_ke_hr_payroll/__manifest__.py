# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Kenyan Payroll',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Store employee tax deduction card forms in the Document app',
    'description': """
Employee Tax Deduction Card forms will be automatically integrated to the Document app.
""",
    'website': ' ',
    'depends': ['documents_hr_payroll', 'l10n_ke_hr_payroll'],
    'data': [
        'views/l10n_ke_tax_deduction_card_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
