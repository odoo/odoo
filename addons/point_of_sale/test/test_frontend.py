
import openerp.tests

@openerp.tests.category('website')
@openerp.tests.at_install(False)
@openerp.tests.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_pos_basic_order(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('pos_basic_order', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.pos_basic_order", login="admin")
