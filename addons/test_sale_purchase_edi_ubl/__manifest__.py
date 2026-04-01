# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Test - Sale & Purchase Order EDI",
    'summary': "Sale & Purchase Order EDI Tests: Ensure Flow Robustness",
    'description': """This module contains tests related to sale and purchase order edi.
    Ensure export and import of order working properly and filling details properly from
    order XML file.""",
    'category': "Hidden",
    'depends': ['purchase_edi_ubl_bis3', 'sale_edi_ubl'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
