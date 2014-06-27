import os

import openerp.tests

inject = [
    ("openerp.Tour", os.path.join(os.path.dirname(__file__), '../../web/static/src/js/tour.js')),
]

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        self.phantom_js("/", "openerp.Tour.run('shop_customize', 'test')", "openerp.Tour.tours.shop_customize", login="admin", inject=inject)
