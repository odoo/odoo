from odoo.tests.common import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestFavorite(HttpCase):
    def test_favorite_management(self):
        self.patch(self.env.registry.get("ir.module.module"), "_order", "sequence desc, id desc")
        self.env["ir.module.module"]._get("l10n_fr").sequence = 100000
        self.start_tour("/odoo/apps", "test_favorite_management", login="admin")
