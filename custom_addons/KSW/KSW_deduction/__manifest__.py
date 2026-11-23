{
    'name': 'KSW Deductions',
    'version': '19.0.1.0.0',
    'summary': 'Manage employee deductions (loans, penalties, advances, etc.)',
    'description': """
Centralized deduction management for KSW payroll.

Categories:
- Borrowed: Employee borrows money with consent (Loan, Salary Advance)
- Company-Paid: Company pays on behalf of employee (Gov Penalty, Internal Penalty)

Loans follow a 5-step approval workflow (DM -> HR -> Accounting -> GM).
Non-loan deductions use instant-apply (draft -> active in one click).

All pending installments are auto-injected as payslip inputs and deducted
via the KSW_DEDUCTIONS salary rule (regular + vacation payslips).
""",
    'author': 'KSW',
    'category': 'Human Resources/Payroll',
    'depends': [
        'hr',
        'hr_holidays',
        'mail',
        'KSW_payroll',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/deduction_type_data.xml',
        'data/salary_rule_deduction.xml',
        'views/ksw_deduction_type_views.xml',
        'views/ksw_deduction_views.xml',
        'views/hr_employee_views.xml',
        'wizard/loan_request_wizard_views.xml',
        'wizard/loan_refuse_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': '_post_init_hook',
}



