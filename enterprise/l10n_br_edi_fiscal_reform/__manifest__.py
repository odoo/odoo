# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Avatax Brazil Fiscal Reform',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['l10n_br_edi'],
    'demo': [
        'data/res_partner_demo.xml',
        'data/product_product_demo.xml',
    ],
    'data': [
        'data/l10n_br.customs.regime.csv',
        'data/l10n_br.nbs.code.csv',
        'data/l10n_br_operation_type_data.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/l10n_br_nbs_code_views.xml',
        'views/l10n_br_customs_regime_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'pre_init_hook': '_pre_init_hook',
}
