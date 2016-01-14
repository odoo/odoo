import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_shop_buy_delivery(self):
        self.phantom_js("/", "openerp.Tour.run('shop_buy_delivery', 'test')", "openerp.Tour.tours.shop_buy_delivery", login="admin")

    def test_02_portal_shop_buy_delivery(self):
        self.phantom_js("/", "openerp.Tour.run('shop_buy_delivery', 'test')", "openerp.Tour.tours.shop_buy_delivery", login="portal")

    def test_03_demo_shop_buy_delivery(self):
        self.phantom_js("/", "openerp.Tour.run('shop_buy_delivery', 'test')", "openerp.Tour.tours.shop_buy_delivery", login="demo")

    def test_04_public_shop_buy_delivery(self):
        self.phantom_js("/", "openerp.Tour.run('shop_buy_delivery', 'test')", "openerp.Tour.tours.shop_buy_delivery")

