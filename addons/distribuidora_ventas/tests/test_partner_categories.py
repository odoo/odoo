from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPartnerCategories(TransactionCase):

    def test_customer_categories_exist(self):
        hotel = self.env.ref('distribuidora_ventas.res_partner_category_hotel')
        supermercado = self.env.ref('distribuidora_ventas.res_partner_category_supermercado')
        restaurante = self.env.ref('distribuidora_ventas.res_partner_category_restaurante')
        self.assertEqual(hotel.name, 'Hotel')
        self.assertEqual(supermercado.name, 'Supermercado')
        self.assertEqual(restaurante.name, 'Restaurante')
