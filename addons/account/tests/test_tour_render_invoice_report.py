# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestTourRenderInvoiceReport(AccountTestInvoicingHttpCommon):

    def setUp(self, chart_template_ref=None):
        super().setUp(chart_template_ref=chart_template_ref)

        self.env.user.write({
            'groups_id': [
                (6, 0, (self.env.ref('account.group_account_invoice') + self.env.ref('base.group_system')).ids),
            ],
        })

        self.out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100.0}),
            ],
        })
        self.out_invoice.post()

        report_layout = self.env.ref('web.report_layout_standard')

        self.company_data['company'].write({
            'primary_color': '#123456',
            'secondary_color': '#789101',
            'external_report_layout_id': report_layout.view_id.id,
        })

        self.env.ref('account.account_invoices_without_payment').report_type = 'qweb-html'

    def test_render_account_document_layout(self):
        self.start_tour('/web', 'account_render_report', login=self.env.user.login, timeout=200)
