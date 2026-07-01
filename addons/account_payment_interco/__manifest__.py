{
    'name': "Intercompany Payment - Account",
    'category': 'Accounting/Accounting',
    'summary': "Enable Intercompany payments to reconcile with their invoices on post.",
    'version': '1.0',
    'depends': ['account_payment', 'sale'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/res_config_settings_views.xml',
    ]
}
