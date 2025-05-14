import odoo
import odoo.tests
import logging

_logger = logging.getLogger(__name__)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippets(odoo.tests.HttpCase):

    def test_01_donation(self):
        payment_demo = self.env['ir.module.module']._get('payment_demo')
        if payment_demo.state != 'installed':
            self.skipTest("payment_demo module is not installed")

        demo_provider = self.env['payment.provider'].search([('code', '=', "demo")])
        demo_provider.write({'state': 'test'})
        self.env.ref('base.user_admin').partner_id.country_id = self.env.ref('base.be')
        self.start_tour("/?enable_editor=1", "donation_snippet_edition", login='admin')
        self.start_tour("/", "donation_snippet_use", login="portal")
