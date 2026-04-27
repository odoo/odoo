# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Field Service Reports - Sale',
    'category': 'Hidden',
    'summary': 'Create Reports for Field service workers',
    'depends': ['industry_fsm_sale', 'industry_fsm_report'],
    'data': [
        'views/product_template_views.xml',
        'views/project_views.xml',
        'views/project_portal_templates.xml',
        'data/industry_fsm_sale_report_data.xml',
    ],
    'demo': [
        'data/industry_fsm_sale_report_demo.xml',
    ],
    'auto_install': True,
    'post_init_hook': 'post_init',
    'assets': {
        'web.assets_backend': [
            'industry_fsm_sale_report/static/src/js/tours/industry_fsm_sale_report_tour.js',
        ],
        'web.assets_frontend': [
            'industry_fsm_sale_report/static/src/js/tours/industry_fsm_sale_report_tour.js',
        ],
    },
    'license': 'OEEL-1',
}
