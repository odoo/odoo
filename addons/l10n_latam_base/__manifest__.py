# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'LATAM Localization Base',
    'category': 'Accounting/Localizations',
    'sequence': 14,
    'author': 'Odoo S.A., ADHOC SA',
    'summary': 'LATAM Localization Base',
    'description': """
Shared base for the Latin American localizations.

It defines the ``latam`` country group and the ``_is_latam`` /
``_get_l10n_latam_base_country_codes`` hooks that the country-specific
localization modules extend, and relabels the partner ``vat`` field as
"Identification Number".

Partner identification beyond the fiscal tax ID (VAT) is handled by the
``additional_identifiers`` mechanism in the ``account`` module.
""",
    'depends': [
        'contacts',
        'base_vat',
    ],
    'data': [
        'data/res_country_group.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_latam_base/static/src/components/select_menu_wrapper/**.*',
        ],
    },
    'license': 'LGPL-3',
}
