# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Kenya eTIMS EDI Integration",
    'summary': """
            Kenya eTIMS Device EDI Integration
        """,
    'description': """
       This module integrates with the Kenyan OSCU eTIMS device.
    """,
    'author': 'Odoo',
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'license': 'OEEL-1',
    'depends': ['l10n_ke', 'product_unspsc'],
    'data': [
        'data/l10n_ke_edi_oscu.code.csv',
        'data/ir_cron_data.xml',
        'data/uom.uom.csv',
        'views/account_tax_views.xml',
        'views/product_views.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/uom_uom_views.xml',
        'views/l10n_ke_edi_oscu_code_views.xml',
        'views/l10n_ke_edi_oscu_notice_views.xml',
        'views/menuitems.xml',
        'security/ir.model.access.csv',
        'wizard/account_move_reversal_view.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_product.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'auto_install': ['l10n_ke'],
}
