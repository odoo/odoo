# -*- encoding: utf-8 -*-
{
    'name': 'Digital Products',
    'version': '0.1',
    'summary': 'Sell digital products in your eCommerce store',
    'category': 'Website/Website',
    'description': """
Sell e-goods in your eCommerce store (e.g. webinars, articles, e-books, video tutorials).
To do so, create the product and attach the file to share via the *Files* button of the product form.
Once the order is paid, the file is made available in the order confirmation page and in the customer portal.
    """,
    'depends': [
        'attachment_indexation',
        'website_sale',
    ],
    'installable': True,
    'data': [
        'views/website_sale_digital.xml',
        'views/website_sale_digital_view.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
}
