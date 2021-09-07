# -*- coding: utf-8 -*-
{
    'name': 'POS Backend Receipt',
    'version': '14.0.0.0',
    'category': 'POS',
    'sequence': 1,
    'summary': 'POS Backend Receipt',
    'description': """
                POS Backend Receipt
    """,
    'depends': ['point_of_sale'],
    'data': [
        'data/order_backend_receipt_paperformat.xml',
        'report/backend_receipt_report_action.xml',
        'report/backend_receipt_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
