import odoo.tests


@odoo.tests.tagged('post_install', '-at_install', 'lpe')
class WebSuite(odoo.tests.HttpCase):

    def test_wowl(self):
        self.browser_js('/wowl/tests', "", "", login='admin', timeout=1800)
