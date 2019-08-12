# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'LATAM Localization Base',
    'version': '13.0.1.0.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'Odoo, ADHOC SA',
    'description': """
Base Module for LATAM Localizations
===================================

* Add Identification Type model to represent valid identifications types in different countries: for AFIP (AR), SII (CL), ...
* Add Countries code defined by government to identify legal entities and natural persons of foreign countries.""",
    'depends': [
        'contacts',
        'base_vat',
    ],
    'data': [
        'data/l10n_latam.identification.type.csv',
        'views/res_partner_view.xml',
        'views/l10n_latam_identification_type_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_set_default_identification_type',
}
