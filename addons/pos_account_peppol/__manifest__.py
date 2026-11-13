# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "POS - Peppol",
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale', 'account_peppol', 'pos_edi_ubl'],
    'data': ['views/res_partner_views.xml'],
    'assets': {
        'point_of_sale._assets_pos': ['pos_account_peppol/static/src/**/*'],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
