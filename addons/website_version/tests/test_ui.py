import openerp.tests

@openerp.tests.category('website')
@openerp.tests.at_install(False)
@openerp.tests.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_versioning(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('versioning', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.versioning", login='admin')