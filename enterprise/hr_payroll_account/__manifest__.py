# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Payroll Accounting',
    'category': 'Human Resources/Payroll',
    'description': """
Generic Payroll system Integrated with Accounting.
==================================================

    * Expense Encoding
    * Payment Encoding
    * Company Contribution Management
    """,
    'depends': ['hr_payroll', 'account_accountant', 'base_iban'],
    'data': [
        'data/hr_payroll_account_data.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_bank_views.xml',
        'report/hr_contract_history_report_views.xml',
    ],
    'demo': [
        'data/hr_payroll_account_demo.xml',
    ],
    'pre_init_hook': '_salaries_account_journal_pre_init',
    'auto_install':  ['hr_payroll', 'account_accountant'],
    'post_init_hook': '_hr_payroll_account_post_init',
    'license': 'OEEL-1',
}
