{
    'name': 'Custom Payroll',
    'version': '1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Custom payroll management with payslip, allowances, and BPJS',
    'description': """
Custom Payroll Module
=====================
- Payroll batch processing per period
- Payslip generation per employee
- Payslip detail components (allowances, deductions, overtime, BPJS)
- Master data for allowances (Tunjangan) and BPJS
- Integration with Employee form
    """,
    'author': 'Konsulta',
    'website': '',
    'depends': [
        'hr',
        'mail',
    ],
    'data': [
        'security/payroll_security.xml',
        'security/ir.model.access.csv',
        'data/payroll_sequence_data.xml',
        'data/payroll_rule_data.xml',
        'views/custom_payroll_tunjangan_views.xml',
        'views/custom_payroll_potongan_tetap_views.xml',
        'views/custom_payroll_bpjs_views.xml',
        'views/custom_payroll_batch_views.xml',
        'views/custom_payroll_slip_detail_views.xml',
        'views/custom_payroll_slip_views.xml',
        'views/custom_payroll_rule_views.xml',
        'views/hr_employee_views.xml',
        'views/payroll_menu.xml',
        'views/custom_payroll_generate_wizard_views.xml',
        'wizard/custom_payroll_reject_wizard_views.xml',
        'report/report_slip_gaji.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
