{
    'name': 'LATAM Localization Base',
    'version': '12.0.1.0.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'Jos/ADHOC SA/Daniel',
    'summary': '',
    'description': """
Base Module for LATAM Localizations
========================================
A lot of Latin American countries need to verify 

* Add Identification Type model to represent valid identifications types in different countries: for AFIP (AR), SII (CL), ...
* Add Countries code defined by AFIP/... to identify legal entities and natural persons of foreign countries.

    """,
    'depends': [
        'contacts',
    ],
    'data': [
        'data/l10n_latam_identification_type_data.xml',
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'views/l10n_latam_identification_type_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
