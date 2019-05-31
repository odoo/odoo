from odoo.tests.common import tagged, HttpCase


@tagged('-at_install', 'post_install', 'document_layout')
class TestAccountDocumentLayout(HttpCase):

    def test_account_document_layout(self):
        company = self.env.company_id
        company.account_onboarding_invoice_layout_state = 'not_done'
        self.start_tour("/web", 'account_dashboard_setup_tour', login='admin')

    def test_render_account_document_layout(self):
        company = self.env.company_id
        report_layout = self.env.ref('web.report_layout_standard')
        company.write({
            'primary_color': '#123456',
            'secondary_color': '#789101',
            'external_report_layout_id': report_layout.view_id.id,
        })
        self.env.ref('account.account_invoices_without_payment').write({
            'report_type': 'qweb-html',
        })
        self.start_tour("/web", 'account_render_report', login='admin', timeout=200)
