# -*- coding: utf-8 -*-

{
    'name': 'Sales Orders Reconciliation',
    'summary': 'Match bank statement transactions with sales orders',
    'version': '1.0',
    'author': 'Odoo SA',
    'category': 'Generic Modules/Accounting',
    'description': """
Sales Orders Reconciliation
===========================

Customers paying sales orders by wire transfer are given a code to put in the memo field.
When you reconcile your bank statements, the transactions corresponding to a sales order payment are matched with the sales order.
    """,
    'depends': ['account', 'sale'],
    'data': [
        'data/sequence_payment_memo.xml',
        'views/account_reconcile_sale_order.xml',
    ],
    'qweb': [
        "static/src/xml/account_reconciliation.xml",
    ],
    'installable': True,
    'license': 'OEEL-1',
}
