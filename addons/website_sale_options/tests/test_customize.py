# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_01_admin_shop_customize_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('shop_customize', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.shop_customize", login="admin")
