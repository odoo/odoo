# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indonesian - Point of Sale',
    # 'icon': '/account/static/description/l10n.png',
    'countries': ['id'],
    'version': '1.0',
    'category': 'Sales/Localizations/Point of Sale',
    'description': """
This is the latest Indonesian Odoo localisation to enable QRIS payment in Point of Sale
=================================================================================================
    - """,
    'author': 'stta-odoo',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/indonesia.html',
    'depends': [
        'l10n_id',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale.assets_prod':[
            'l10n_id_pos/static/src/app/utils/qr_code_popup/*',
            'l10n_id_pos/static/src/app/store/*',
        ]
    },
    'license': 'LGPL-3',
}
