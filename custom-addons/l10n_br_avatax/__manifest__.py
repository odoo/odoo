# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Avatax Brazil',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['iap', 'l10n_br', 'account_external_tax'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_tax_views.xml',
        'views/account_fiscal_position_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/ir_logging_views.xml',
        'views/res_config_settings_views.xml',
        'data/l10n_br.ncm.code.csv',
        'data/product_product.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/product_product_demo.xml',
    ],
    'license': 'OEEL-1',
    'post_init_hook': 'post_init',
}
