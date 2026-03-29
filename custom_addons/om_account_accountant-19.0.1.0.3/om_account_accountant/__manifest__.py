{
    'name': 'Accountant',
    'version': '1.0.3',
    'category': 'Accounting',
    'summary': 'Your friendly neighborhood accountant for all your financial needs.',
#    'summary': 'Accounting Reports, Asset Management and Budget, Recurring Payments, '
#               'Lock Dates, Fiscal Year, Accounting Dashboard, Financial Reports, '
#               'Customer Follow up Management, Bank Statement Import',
    'description': 'Kodoo 19 Financial Reports, Asset Management and '
                   'Budget, Financial Reports, Recurring Payments, '
                   'Bank Statement Import, Customer Follow Up Management,'
                   'Account Lock Date, Accounting Dashboard',
#    'live_test_url': 'https://www.youtube.com/c/OdooMates',
    'sequence': '1',
    'website': 'https://www.walnutit.com',
    'author': 'bootstrapprx,Odoo Mates, Walnut Software Solutions, Odoo SA',
    'maintainer': 'bootstrapprx, Odoo Mates, Walnut Software Solutions',
    'license': 'LGPL-3',
    'support': 'odoomates@gmail.com',
    'depends': [
        'accounting_pdf_reports',
        'om_account_asset',
        'om_account_budget',
        'om_fiscal_year',
        'om_recurring_payments',
        'om_account_daily_reports',
        'om_account_followup',
    ],
    'data': [
        'security/group.xml',
        'views/menu.xml',
        'views/settings.xml',
        'views/account_group.xml',
        'views/account_tag.xml',
        'views/res_partner.xml',
        'views/account_bank_statement.xml',
        'views/payment_method.xml',
        'views/reconciliation.xml',
        'views/account_journal.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'application': True,
    'images': ['static/description/banner.gif'],
}
