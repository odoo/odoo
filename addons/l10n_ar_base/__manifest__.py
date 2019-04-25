{
    'name': 'Argentinian Localization Base',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'ADHOC SA',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Base Module for Argentinian Localization
========================================

* Configure data for used currencies.
   * Principal one os ARS.
   * Conventions for the most used secondary currencies USD and EUR.
* Add Argentinian Banks data enable by BCRA (Central Bank of Argentina) to operate in the country.
* Add new field named CBU to bank model.
* Add Identification Category model to represent AFIP valid identifications types.
* Add Res Partner titles used in Argentina to identify the types of legal entities (SA, SRL, etc).
* Add Countries code defined by AFIP to identify legal entities and natural persons of foreign countries.

    """,
    'depends': [
        'base',
        'contacts',
    ],
    'data': [
        'data/res_currency_data.xml',
        'data/res_bank_data.xml',
        'data/l10n_ar_id_category_data.xml',
        'data/res_partner_title_data.xml',
        'data/res_country_data.xml',
        'views/res_partner_bank_views.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/l10n_ar_id_category_view.xml',
        'views/res_country_view.xml',
        'wizards/res_config_settings_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/partner_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
}
