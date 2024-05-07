{
    'name': "Spain - EDI",
    'countries': ['es'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': "This module provides helpers for the different spain edi.",
    'depends': [
        'l10n_es',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/l10n_es_edi_certificate.xml',

        'views/l10n_es_edi_certificate_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}
