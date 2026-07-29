# Part of the PoC integration Odoo <-> API_Hacienda (CRLibre).
{
    'name': "Costa Rica - Factura Electrónica (PoC CRLibre)",
    'version': '19.0.1.0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': "PoC: genera clave y XML de FE v4.4 vía API_Hacienda de CRLibre",
    'author': "PoC Odoo x API_Hacienda (CRLibre)",
    'depends': ['account', 'l10n_cr'],
    'data': [
        'data/system_params.xml',
        'security/l10n_cr_fe_security.xml',
        'security/ir.model.access.csv',
        'views/fe_config_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_move_reversal_views.xml',
        'views/proveedor_upload_views.xml',
        'data/mail_template.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
