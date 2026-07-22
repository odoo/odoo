from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMenuOverrides(TransactionCase):

    def test_contacts_menu_renamed_to_clientes(self):
        menu = self.env.ref('contacts.menu_contacts')
        for lang, _lang_name in self.env['res.lang'].get_installed():
            self.assertEqual(menu.with_context(lang=lang).name, 'Clientes')

    def test_sale_menu_renamed_to_preventas(self):
        menu = self.env.ref('sale.sale_menu_root')
        for lang, _lang_name in self.env['res.lang'].get_installed():
            self.assertEqual(menu.with_context(lang=lang).name, 'Preventas')

    def test_point_of_sale_menu_is_hidden(self):
        menu = self.env.ref('point_of_sale.menu_point_root')
        self.assertFalse(menu.active)

    def test_productos_menu_is_root_app_pointing_to_sale_catalog(self):
        menu = self.env.ref('distribuidora_config.menu_productos_root')
        self.assertFalse(menu.parent_id, "debe ser un menu raiz para aparecer en el switcher de apps")
        self.assertEqual(menu.action.id, self.env.ref('sale.product_template_action').id)
        self.assertEqual(menu.sequence, 32)

    def test_crm_menu_is_hidden(self):
        menu = self.env.ref('crm.crm_menu_root')
        self.assertFalse(menu.active)
