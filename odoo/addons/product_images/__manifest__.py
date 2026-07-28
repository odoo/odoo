# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Images',
    'version': '1.0',
    'description': """
Automatically set product images based on the barcode
=====================================================

This module integrates with the Google Custom Search API to set images on products based on the
barcode.
    """,
    'license': 'LGPL-3',
    'category': 'Technical',
    'depends': ['product'],
    'data': [
        'data/ir_cron_data.xml',
        'security/product_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/product_fetch_image_wizard_views.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
}
