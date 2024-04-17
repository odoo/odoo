# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sales PDF Quotation Builder",
    'category': 'Sales/Sales',
    'description': "Build nice quotations",
    'depends': ['sale_management'],
    'data': [
        'data/ir_config_parameters.xml',

        'report/ir_actions_report.xml',

        'security/ir.model.access.csv',

        'views/product_document_views.xml',
        'views/sale_order_template_views.xml',

        'wizards/dynamic_fields_wizard_views.xml',
        'wizards/res_config_settings_views.xml',
    ],
    'demo': [
        'data/sale_pdf_quote_builder_demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
