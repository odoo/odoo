from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestListaPreciosMenu(TransactionCase):

    def test_menu_is_top_level_and_points_to_pricelist_action(self):
        menu = self.env.ref('distribuidora_ventas.menu_lista_precios_root')
        self.assertFalse(menu.parent_id)
        self.assertEqual(menu.action.res_model, 'product.pricelist')
