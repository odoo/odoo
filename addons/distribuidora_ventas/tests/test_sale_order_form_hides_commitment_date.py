import re

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOrderFormHidesCommitmentDate(TransactionCase):

    def test_shipping_group_is_invisible(self):
        view = self.env['sale.order'].get_view(view_type='form')
        match = re.search(r'<group[^>]*name="sale_shipping"[^>]*>', view['arch'])
        self.assertIsNotNone(match, "no se encontro el grupo 'sale_shipping' en la vista combinada")
        self.assertIn('invisible', match.group(0))
