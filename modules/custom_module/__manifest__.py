# __manifest__.py
{
    'name': 'Custom Module',
    'version': '1.0',
    'depends': ['base', 'web','pos_self_order', 'point_of_sale', 'base_import', 'pos_restaurant','bus', 'pos_hr'],
    'data': [
        #'security/ir.model.access.csv',
        #'views/pos_assets_index_inherit.xml',
        # Category module
        #'views/categories/list_pos_category.xml',
        #'views/categories/upsert_pos_category.xml',
        # Menus module
        #'views/menus/list_menu.xml',
        #'views/menus/upsert_menu.xml',
        #'views/menus/tree_products.xml',
        # Restaurants module
        #'views/restaurants/list_res_company.xml',
        #'views/restaurants/upsert_res_company.xml',

    ],

    'assets': {
            'web.assets_backend': [
                'custom_module/static/src/xml/custom_button.xml',
                'custom_module/static/src/js/custom_button.js',
                'custom_module/static/src/js/synchronize_dialog.js',
                'custom_module/static/src/scss/styles.scss',
                'custom_module/static/src/img/favicon.ico',
                'custom_module/static/src/scss/custom_pwa.scss',
                'custom_module/static/src/scss/login_screen.scss',
            ],
            'web.assets_frontend' : [
                'custom_module/static/src/scss/login.scss',
                'custom_module/static/src/scss/login_screen.scss',

            ],
            'point_of_sale._assets_pos': [
                'custom_module/static/src/scss/pos.scss',
                'custom_module/static/src/scss/receipt.scss',
                'custom_module/static/src/css/pos_receipt.css',
                'custom_module/static/src/scss/login_screen.scss',
                'custom_module/static/src/xml/saver_screen_inherit.xml',
                'custom_module/static/src/xml/cashier_name_inherit.xml',
                #'custom_module/static/src/js/pos_navbar_inherit.js',
                #'custom_module/static/src/xml/pos_navbar_inherit.xml',
                'custom_module/static/src/js/pos_store_inherit.js',

            ],
    },
    'images': [
        'static/img/logo.png'
    ],
}


