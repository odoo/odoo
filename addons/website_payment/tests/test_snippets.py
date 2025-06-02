from odoo.tests.common import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tagged('post_install', '-at_install')
class TestSnippets(HttpCaseWithUserPortal):

    def setUp(self):
        super().setUp()

        payment_demo = self.env['ir.module.module']._get('payment_demo')
        if payment_demo.state != 'installed':
            self.skipTest("payment_demo module is not installed")

        demo_provider = self.env['payment.provider'].search([('code', '=', "demo")])
        demo_provider.write({'state': 'test'})

        belgium = self.env.ref('base.be')

        self.env.ref('base.user_admin').write({
            'country_id': belgium.id,
            'email': 'mitchell.admin@example.com',
        })
        self.env.company.write({
            'email': 'no-reply@company.com',
        })

        self.user_portal.country_id = belgium.id

    def test_01_donation(self):
        self.start_tour("/?enable_editor=1", "donation_snippet_edition", login='admin')
        self.start_tour("/", "donation_snippet_use", login="portal")
        self.start_tour("/?enable_editor=1", "donation_snippet_edition_2", login='admin')
        self.start_tour("/", "donation_snippet_use_2", login="portal")

    def test_02_donation_form_custom_field(self):
        self.start_tour("/donation/pay", "donation_form_custom_field_create", login="admin")
        self.start_tour("/donation/pay", "donation_form_custom_field_submit", login="portal")
