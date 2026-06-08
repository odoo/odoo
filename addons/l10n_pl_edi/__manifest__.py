{
    'name': 'Polish E-Invoicing FA(3)',
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'summary': 'Support for FA(3) electronic invoices in Poland via KSeF',
    'description': """Export FA(3) compliant XML invoices and prepare for integration with KSeF.""",
    'data': [
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron_data.xml',
        'data/fa3_template.xml',
    ],
    'demo': [
        'demo/account_invoice_demo.xml',
    ],
    'depends': [
        'l10n_pl',
        'certificate'
    ],
    'auto_install': ['l10n_pl'],
    'license': 'LGPL-3',
}
