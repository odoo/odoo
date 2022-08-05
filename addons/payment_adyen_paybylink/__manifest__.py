# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Adyen Payment Acquirer/Pay by Link Patch",
    'category': 'Accounting',
    'summary': "Payment Acquirer: Adyen Pay by Link Patch",
    'version': '1.0',
    'description': """ This module migrates the Adyen implementation from 
        the Hosted Payment Pages API to the Pay by Link API. """,
    'depends': ['payment_adyen'],
    'data': [
        'data/payment_acquirer_data.xml',
        'views/payment_views.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'license': 'LGPL-3'
}
