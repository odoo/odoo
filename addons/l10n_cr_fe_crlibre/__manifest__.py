# Part of the PoC integration Odoo <-> API_Hacienda (CRLibre).
{
    'name': "Costa Rica - Factura Electrónica (PoC CRLibre)",
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': "PoC: genera clave y XML de FE v4.4 vía API_Hacienda de CRLibre",
    'author': "PoC Odoo x API_Hacienda (CRLibre)",
    'depends': ['account', 'l10n_cr'],
    'data': [
        'data/config_params.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
