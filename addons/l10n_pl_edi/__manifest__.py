{
    'name': 'Polish E-Invoicing FA(3)',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Support for FA(3) electronic invoices in Poland via KSeF',
    'description': """Export FA(3) compliant XML invoices and prepare for integration with KSeF.""",
    'data': [
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'data/fa3_template.xml'
    ],
    'depends': [
        'l10n_pl',
        'account_edi_proxy_client',
    ],
    'auto_install': ['l10n_pl'],
    'installable': True,
    'license': 'LGPL-3',
}
