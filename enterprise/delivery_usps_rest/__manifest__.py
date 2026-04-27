# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "United States Postal Service (USPS) Shipping",
    'description': "Send your shippings through USPS and track them online.  This version of the USPS connector is"
                   "compatible with the new USPS REST API available at https://developers.usps.com/.",
    'category': 'Inventory/Delivery',
    'sequence': 305,
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_usps_data.xml',
        'views/delivery_usps_view.xml',
    ],
    'license': 'OEEL-1',
}
