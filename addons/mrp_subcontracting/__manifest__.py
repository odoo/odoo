# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "mrp_subcontracting",
    'version': '0.1',
    'summary': "Subcontract Productions",
    'website': 'https://www.odoo.com/app/manufacturing',
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp'],
    'data': [
        'data/mrp_subcontracting_data.xml',
        'security/mrp_subcontracting_security.xml',
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml',
        'views/res_partner_views.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_move_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_picking_views.xml',
        'views/supplier_info_views.xml',
        'views/product_views.xml',
        'views/mrp_production_views.xml',
        'views/subcontracting_portal_views.xml',
        'views/subcontracting_portal_templates.xml',
        'views/stock_location_views.xml',
        'wizard/stock_picking_return_views.xml',
    ],
    'demo': [
        'data/mrp_subcontracting_demo.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'mrp_subcontracting/static/tests/tours/subcontracting_portal_tour.js',
        ],
        'web.assets_backend': [
            'mrp_subcontracting/static/src/components/**/*.js',
        ],
        'web.assets_qweb': [
            'mrp_subcontracting/static/**/*.xml',
        ],
        'mrp_subcontracting.assets_qweb': [
            ('include', 'web.assets_qweb'),
            'mrp_subcontracting/static/src/subcontracting_portal/subcontracting_portal.xml',
        ],
        'mrp_subcontracting.webclient': [
            ('include', 'web.assets_backend'),
            ('remove', 'web/static/src/webclient/menus/*.js'),
            'mrp_subcontracting/static/src/subcontracting_portal/main.js',
            'mrp_subcontracting/static/src/subcontracting_portal/subcontracting_portal.js',
            'mrp_subcontracting/static/src/subcontracting_portal/picking_form_controller.js',
            'mrp_subcontracting/static/src/subcontracting_portal/move_list_view.js',
            'web/static/src/start.js',
            'web/static/src/legacy/legacy_setup.js',
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
