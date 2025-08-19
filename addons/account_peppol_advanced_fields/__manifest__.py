{
    'name': "Account Peppol Advanced Fields",
    'summary': "Adds specific Peppol fields to invoices under an 'Additional Information' tab.",
    'description': """
        This module introduces several advanced Peppol-related fields to the Odoo
        invoice model (`account.move`) and makes them available on a new 'Additional
        Information' tab within the 'Other Info' section of the invoice form view.
        This is designed as a separate, optional module to keep core functionality
        clean and allow for flexible use cases.
    """,
    'author': "Odoo S.A.",
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account', 'account_edi_ubl_cii'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
