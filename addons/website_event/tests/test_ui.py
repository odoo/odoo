import openerp.tests

@openerp.tests.category('website')
@openerp.tests.at_install(False)
@openerp.tests.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('event', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.event", login='admin')
