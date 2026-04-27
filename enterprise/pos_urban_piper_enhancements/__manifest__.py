{
    'name': 'Point of Sale - UrbanPiper Enhancements',
    'category': 'Sales/Point of Sale',
    'description': """
Enhancements for the Point of Sale UrbanPiper module. Includes features such as store timing configuration, scheduled order handling, and improved toggle options.
    """,
    'depends': ['pos_urban_piper'],
    'data': [
        'data/ir_cron.xml',
        'data/pos_store_timing_data.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
        'views/pos_store_time_views.xml',
        'views/report_invoice.xml',
        'views/product_attribute_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_urban_piper_enhancements/static/src/point_of_sale_override/**/*',
        ],
        'pos_preparation_display.assets': [
            'pos_urban_piper_enhancements/static/src/pos_preparation_display_override/**/*',
            'pos_urban_piper/static/src/utils.js',
        ]
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
