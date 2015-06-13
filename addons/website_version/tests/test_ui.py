import openerp.tests


@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_versioning(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('versioning', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.versioning", login='admin')