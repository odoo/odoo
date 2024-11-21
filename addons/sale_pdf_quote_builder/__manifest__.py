# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sales PDF Quotation Builder",
    'category': 'Sales/Sales',
    'description': "Build nice quotations",
    'depends': ['sale_management'],
    'data': [
        'data/ir_cron.xml',
        'data/sale_pdf_form_field.xml',

        'report/ir_actions_report.xml',

        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        'views/product_document_views.xml',
        'views/quotation_document_views.xml',
        'views/sale_order_template_views.xml',
        'views/sale_order_views.xml',
        'views/sale_pdf_form_field_views.xml',
        'views/sale_pdf_quote_builder_menus.xml',

        'wizards/res_config_settings_views.xml',
    ],
    'demo': [
        'data/sale_pdf_quote_builder_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'sale_pdf_quote_builder/static/src/js/**/*',
        ],
        'web.assets_tests': [
            'sale_pdf_quote_builder/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
