# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged, loaded_demo_data

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAddToCartSnippet(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a dummy payment provider to ensure that the tour has at least one available to it.
        arch = """
        <form action="dummy" method="post">
            <input type="hidden" name="view_id" t-att-value="viewid"/>
            <input type="hidden" name="user_id" t-att-value="user_id.id"/>
        </form>
        """
        redirect_form = cls.env['ir.ui.view'].create({
            'name': "Dummy Redirect Form",
            'type': 'qweb',
            'arch': arch,
        })
        cls.dummy_provider = cls.env['payment.provider'].create({
            'name': "Dummy Provider",
            'code': 'none',
            'state': 'test',
            'is_published': True,
            'allow_tokenization': True,
            'redirect_form_view_id': redirect_form.id,
        })

    def test_configure_product(self):
        # Reset the company country id, which ensure that no country dependant fields are blocking the address form.
        self.env.company.country_id = self.env.ref('base.us')
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour("/", 'add_to_cart_snippet_tour', login="admin")
