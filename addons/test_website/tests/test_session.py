import odoo.tests


class TestWebsiteSession(odoo.tests.HttpCase):

    def test_01_run_test(self):
        self.start_tour('/', 'test_json_auth')
