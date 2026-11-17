# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from .common import SeAccountTestCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeInvoice(SeAccountTestCommon):

    def test_invoice_f_tax_text(self):
        report = self.env['ir.actions.report']
        invoice = self._invoice('out_invoice')
        refund = self._invoice('out_refund')
        self.env.company.l10n_se_f_tax_approved = False
        html = report._render_qweb_html('account.report_invoice', invoice.ids)[0].decode()
        self.assertNotIn('Approved for F-tax', html)
        self.env.company.l10n_se_f_tax_approved = True
        for move in (invoice, refund):
            with self.subTest(move_type=move.move_type):
                html = report._render_qweb_html('account.report_invoice', move.ids)[0].decode()
                self.assertIn('Approved for F-tax', html)
