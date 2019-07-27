{
    'name': 'Base for Chilean Localization',
    'version': '1.0.0',
    'category': 'Localization',
    'sequence': 10,
    'author': 'Blanco Martin & Asociados',
    'description': """
Base Module for Chilean Localization
=====================================
* Activate CLP, currency and UF and UTM indexes as currency.
    """,
    'depends': [
        'contacts',
        'base_address_city',
        'base_vat',
        'l10n_latam_base'
    ],
    'data': [
        'data/l10n_latam_identification_type_data.xml',
        'data/res.bank.csv',
        'data/res.currency.csv',
        'views/res_bank_view.xml',
        'views/res_company_view.xml',
        'views/res_country_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'demo': [
        # 'demo/partner_demo.xml',
    ],
}