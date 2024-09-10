import odoo
import odoo.tests
import logging

_logger = logging.getLogger(__name__)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippets(odoo.tests.HttpCase):

    def test_01_donation(self):
        if not odoo.tests.loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour("/?enable_editor=1", "donation_snippet_edition", login='admin')
