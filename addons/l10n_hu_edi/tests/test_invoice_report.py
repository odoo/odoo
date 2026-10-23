# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests.common import tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nHuEdiInvoiceReport(L10nHuEdiTestCommon):

    def _get_invoice_date_label(self, move):
        report_html = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', move.ids)[0]
        labels = html.fromstring(report_html).xpath("//div[@name='invoice_date']/strong")
        self.assertEqual(len(labels), 1)
        return labels[0].text_content().strip()

    def test_invoice_report_invoice_date_label(self):
        """ account_debit_note puts its own label first in the invoice date block: the Hungarian
        report must not turn it into the label of every invoice. """
        invoice = self.create_invoice_simple()
        invoice.action_post()
        self.assertEqual(self._get_invoice_date_label(invoice), 'Invoice Date')

        credit_note = self.create_reversal(invoice)
        self.assertEqual(self._get_invoice_date_label(credit_note), 'Credit Note Date')

        refund = self.create_credit_note_simple()
        refund.action_post()
        self.assertEqual(self._get_invoice_date_label(refund), 'Invoice Date')

        self.env['account.debit.note'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'reason': 'Test debit note',
            'copy_lines': True,
        }).create_debit()
        debit_note = invoice.debit_note_ids
        if debit_note.state == 'draft':
            debit_note.action_post()
        self.assertEqual(self._get_invoice_date_label(debit_note), 'Debit Note Date')
