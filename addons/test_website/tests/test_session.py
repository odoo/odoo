import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSession(odoo.tests.HttpCase):

    def test_01_run_test(self):
        self.start_tour('/', 'test_json_auth')

    def test_02_inactive_session_lang(self):
        session = self.authenticate(None, None)
        self.env.ref('base.lang_fr').active = False
        session.context['lang'] = 'fr_FR'
        odoo.http.root.session_store.save(session)
        res = self.url_open('/test_website_sitemap')  # any auth='public' route would do
        res.raise_for_status()
