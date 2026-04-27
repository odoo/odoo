# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Arab Emirates - Payroll',
    'countries': ['ae'],
    'category': 'Human Resources/Payroll',
    'description': """
United Arab Emirates Payroll and End of Service rules.
=======================================================
- Basic salary calculations
- EOS calculations
- Annual leaves provisions and EOS provisions
- Social insurance rules for locals
- Overtime rule for the other inputs case
- Sick-leaves calculations
- DEWS calculations
- EOS calculations for free zones (DMCC)
- Out of contract calculations
- Calculation for unused leaves for EOS calculation
- Additional other input rules for (bonus, commissions, arrears, etc.)
- Master payroll export
- WPS
    """,
    'depends': ['hr_payroll', 'hr_work_entry_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payroll_report.xml',
        'views/report_payslip_templates.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_work_entry_type.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_rule_parameter_data.xml',
        'data/hr_leave_type_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_payroll_master_report_views.xml',
        'views/res_bank_views.xml',
        'views/res_config_settings_view.xml',
        'views/hr_leave_type_views.xml',
        'wizard/hr_payroll_payment_report_wizard.xml',
    ],
    'demo': [
        'data/l10n_ae_hr_payroll_demo.xml'
    ],
    'license': 'OEEL-1',
    'auto_install': True
}
