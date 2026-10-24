{
    'name': 'Point of Sale UBL',
    'author': 'Odoo S.A.',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'UBL in the Point of Sale ',
    'description': """

This module provides helpers for exporting POS orders in various UBL 2.1 formats.

""",
    'data': ['views/res_partner_views.xml'],
    'depends': ['point_of_sale', 'account_edi_ubl_cii'],
    'license': 'LGPL-3',
}
