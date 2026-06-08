from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestApiDocTour(HttpCase):

    def test_api_doc_simple_start(self):
        wait_for_app_to_load = "document.querySelector('.o-doc-client-root') !== null"

        test_script = """
            const searchInput = document.querySelector('header input[placeholder="Find anything..."]');

            if (!searchInput) {
                console.error("Test Failed: The doc header was not found in the DOM.");
            } else {
                console.log('test successful');
            }
        """

        self.browser_js(
            url_path="/doc",
            code=test_script,
            ready=wait_for_app_to_load,
            login="admin",
        )
