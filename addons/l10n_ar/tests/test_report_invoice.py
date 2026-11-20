# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import html

from odoo.tests import tagged

from . import common


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestArReportInvoice(common.TestArCommon):

    def test_invoice_header_logo_size(self):
        """The logo in the AR custom header must use the standard report logo
        class instead of a fixed inline height."""
        self.company_ri.logo = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg=='
        invoice = self._create_invoice_ar()
        self._post(invoice)
        self.assertEqual(invoice._get_name_invoice_report(), 'l10n_ar.report_invoice_document')

        content = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)[0]
        logo = html.fromstring(content).xpath("//div[@name='left-upper-side']/img")
        self.assertEqual(len(logo), 1, "The AR custom header should render the company logo.")
        self.assertIn('o_company_logo_big', logo[0].get('class', '').split())
        self.assertFalse(logo[0].get('style'), "The logo should not have a fixed inline size.")
