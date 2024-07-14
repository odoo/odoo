# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Master Production Schedule',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 50,
    'summary': 'Master Production Schedule',
    'depends': ['base_import', 'mrp', 'purchase_stock'],
    'description': """
Master Production Schedule
==========================

Sometimes you need to create the purchase orders for the components of
manufacturing orders that will only be created later.  Or for production orders
where you will only have the sales orders later.  The solution is to predict
your sale forecasts and based on that you will already create some production
orders or purchase orders.

You need to choose the products you want to add to the report.  You can choose
the period for the report: day, week, month, ...  It is also possible to define
safety stock, min/max to supply and to manually override the amount you will
procure.
""",
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_mps_security.xml',
        'views/mrp_mps_views.xml',
        'views/mrp_mps_menu_views.xml',
        'views/mrp_bom_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/mrp_mps_forecast_details_views.xml'
    ],
    'demo': [
        'data/mps_demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'mrp_mps/static/src/**/*',
        ],
    }
}
