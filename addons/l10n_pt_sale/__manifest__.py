# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Sale',
    'description': """Certification requirements for the quotations (OR) and sales orders (NE) of Portuguese companies:
numbered in AT series, signed, locked once issued, and printed with their ATCUD and QR code.""",
    'category': 'Accounting/Localizations/Sale',
    'depends': [
        'l10n_pt_certification',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/l10n_pt_at_series_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_portal_templates.xml',
        'report/ir_actions_report_templates.xml',
        'report/l10n_pt_sale_hash_integrity_templates.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
