# -*- coding: utf-8 -*-

{
    'name': 'Product Email Template',
    'depends': ['account'],
    'category': 'Accounting/Accounting',
    'description': """
Add email templates to products to be sent on invoice confirmation
==================================================================

With this module, link your products to a template to send complete information and tools to your customer.
For instance when invoicing a training, the training agenda and materials will automatically be sent to your customers.'
    """,
    'data': [
        'views/product_views.xml',
        'views/mail_template_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
