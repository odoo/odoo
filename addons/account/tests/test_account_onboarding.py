from odoo.tests.common import tagged, HttpCase


@tagged('-at_install', 'post_install', 'document_layout')
class TestAccountDocumentLayout(HttpCase):

    def test_account_document_layout(self):
        company = self.env.company_id
        company.account_onboarding_invoice_layout_state = 'not_done'
        self.start_tour("/web", 'account_dashboard_setup_tour', login='admin')
