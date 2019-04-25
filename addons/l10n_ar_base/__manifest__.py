{
    'name': 'Argentinian Localization Base',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'ADHOC SA',
    'summary': '',
    'description': """
Base Module for Argentinian Localization
========================================

* Activate ARS currency.
* Add Identification Type model to represent AFIP valid identifications types.
* Add Countries code defined by AFIP to identify legal entities and natural persons of foreign countries.
* Add new field named CBU to bank model.
    """,
    'depends': [
        'base',
        'contacts',
    ],
    'data': [
        'data/res_currency_data.xml',
        'data/l10n_ar_identification_type_data.xml',
        'data/res_country_data.xml',
        'views/res_partner_bank_views.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/l10n_ar_identification_type_view.xml',
        'views/res_country_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/partner_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
}
