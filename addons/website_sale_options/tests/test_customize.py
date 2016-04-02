import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_shop_customize_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('shop_customize', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.shop_customize", login="admin")
