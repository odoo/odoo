{
    'name': "SEPA Credit Transfer / ISO20022",
    'summary': """Export payments as SEPA Credit Transfer or ISO20022 files""",
    'category': 'Accounting/Accounting',
    'description': """
Generate XML payment orders as recommended by the SEPA and ISO20022 norms.
    """,
    'version': '1.0',
    'depends': ['account_batch_payment', 'base_iban'],
    'data': [
        'data/account_payment_method.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_journal_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_batch_payment_views.xml',
        'views/account_payment_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    'post_init_hook': 'init_initiating_party_names',
    'license': 'OEEL-1',
}
