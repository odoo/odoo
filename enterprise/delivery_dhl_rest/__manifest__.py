# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "DHL Express Shipping",
    'description': "Send your shippings through DHL and track them online. This version of the DHL connector is"
                   "compatible with the DHL REST API available at https://developer.dhl.com/. It is no longer"
                   "compatible with the older DHL SOAP APIs (which have their own credentials).",
    'category': 'Inventory/Delivery',
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_dhl_data.xml',
        'views/delivery_dhl_view.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'OEEL-1',
}
