from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMenuOverrides(TransactionCase):

    def test_contacts_menu_renamed_to_clientes(self):
        menu = self.env.ref('contacts.menu_contacts')
        self.assertEqual(menu.name, 'Clientes')

    def test_sale_menu_renamed_to_preventas(self):
        menu = self.env.ref('sale.sale_menu_root')
        self.assertEqual(menu.name, 'Preventas')

    def test_point_of_sale_menu_is_hidden(self):
        menu = self.env.ref('point_of_sale.menu_point_root')
        self.assertFalse(menu.active)
