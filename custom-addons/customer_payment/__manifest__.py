{
    'name': 'Customer Payment Tracking',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Track customer payments and invoices from POS',
    'description': """
        Customer Payment Tracking
        =========================
        This module allows you to track customer payments and view their invoice history.

        Features:
        ---------
        * Create payment records for customers
        * View all invoices for a customer by year
        * Record multiple payment entries with dates and amounts
        * Compare total invoices vs total payments
        * Running balance fields on invoice reports showing cumulative totals and payments
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['point_of_sale', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/customer_payment_views.xml',
        'views/menu_views.xml',
        'views/report_invoice.xml',
        'views/report_customer_payment.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
