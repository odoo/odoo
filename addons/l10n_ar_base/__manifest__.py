{
    'name': 'Argentinian Localization Base',
    'version': '12.0.1.0.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'ADHOC SA',
    'summary': '',
    'description': """
Base Module for Argentinian Localization
========================================

* Activate ARS currency.
* Add Identification Type to represent AFIP valid identifications types.
* Add Countries code defined by AFIP to identify legal entities and natural persons of foreign countries.
    """,
    'depends': [
        'l10n_latam_base',
        'base_vat',
    ],
    'data': [
        'data/res_currency_data.xml',
        'data/l10n_latam_identification_type_data.xml',
        'data/res_country_data.xml',
        'views/res_country_view.xml',
    ],
    'demo': [
        'demo/partner_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
