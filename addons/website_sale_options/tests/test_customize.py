import openerp.tests


class TestUi(openerp.tests.HttpCase):

    post_install = True
    at_install = False

    def test_01_admin_shop_customize_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_customize')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_customize", login="admin")
