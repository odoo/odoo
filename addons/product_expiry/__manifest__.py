# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Products Expiration Date',
    'category': 'Inventory/Inventory',
    'depends': ['stock'],
    'description': """
Track different dates on products and production lots.
======================================================

Following dates can be tracked:
-------------------------------
    - end of life
    - best before date
    - removal date
    - alert date

Also implements the removal strategy First Expiry First Out (FEFO) widely used, for example, in food industries.
""",
    'data': ['security/ir.model.access.csv',
             'security/stock_security.xml',
             'views/production_lot_views.xml',
             'views/product_template_views.xml',
             'views/res_config_settings_views.xml',
             'views/stock_move_views.xml',
             'views/stock_quant_views.xml',
             'wizard/confirm_expiry_view.xml',
             'report/report_deliveryslip.xml',
             'report/report_lot_barcode.xml',
             'report/report_package_barcode.xml',
             'data/product_expiry_data.xml',
             'data/mail_activity_type_data.xml',
            ],
    'license': 'LGPL-3',
}
