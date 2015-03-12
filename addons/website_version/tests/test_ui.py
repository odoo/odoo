import openerp.tests


@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_01_versioning(self):
        self.phantom_js("/", "openerp.Tour.run('versioning', 'test')", "openerp.Tour.tours.versioning", login='admin')