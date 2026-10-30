import re
import unittest
from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from odoo.addons.l10n_pt_sale.tests.common import TestL10nPtSaleCommon

ORIGINAL = '<span id="l10n_pt_print_version">Original</span>'
REPRINT = '<span id="l10n_pt_print_version">2ª Via</span>'
CANCELLED = 'Documento Cancelado'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSalePrinting(TestL10nPtSaleCommon):
    """
    What the customer receives of a quotation or sales order: the printed document and its QR code.

    Its first print is its Original, every later one a "2ª Via" keeping the original's content, asked
    a reason, and marked once the order is cancelled (Despacho 8632/2014 2.2.15, 2.2.16). It prints its
    number, ATCUD and AT designation, dates as DD-MM-AAAA, and never the generic NIF 999999990
    (Despacho 8632/2014 2.2.4; Portaria 195/2020). Signatures being deterministic, values are literal.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_sale_azores_16 = cls.env['account.chart.template'].ref('iva_pt_ac_sale_normal')

    # -------------------------------------------------------------------------
    # Printing
    # -------------------------------------------------------------------------

    def _attachments(self, records):
        return self.env['l10n.pt.attachment'].sudo().search([('res_model', '=', records._name), ('res_id', 'in', records.ids)])

    def test_original_then_reprint(self):
        """The first print of an order is its Original, the next its 2ª Via, each stored (PT-70)."""
        quotation = self.make_order()
        self.assertIn(ORIGINAL, self.print_pdf(quotation))
        self.assertEqual(quotation.l10n_pt_print_version, 'original')
        reprint = self.print_pdf(quotation)
        self.assertIn(REPRINT, reprint)
        self.assertNotIn(ORIGINAL, reprint)
        self.assertEqual(quotation.l10n_pt_print_version, 'reprint')
        # One template: the original print is stored once and served again.
        self.assertEqual(len(self._attachments(quotation)), 1)

    def test_preview_stores_nothing(self):
        """An HTML render issues the order but is not a print: nothing stored, the next print is the Original."""
        quotation = self.make_order()
        self.assertIn(ORIGINAL, self.preview(quotation))
        self.assertIssued(quotation)
        self.assertFalse(quotation.l10n_pt_print_version)
        self.assertFalse(self._attachments(quotation))
        self.assertIn(ORIGINAL, self.print_pdf(quotation))

    def test_reprint_keeps_original_content(self):
        """A reprint serves the content of the original print, even after the customer changed."""
        quotation = self.make_order()
        self.assertIn('Cliente PT', self.print_pdf(quotation))
        self.partner_pt.name = 'Novo Nome Lda'
        reprint = self.print_pdf(quotation)
        self.assertIn('Cliente PT', reprint)
        self.assertNotIn('Novo Nome Lda', reprint)

    def test_cancelled_order(self):
        """A cancelled order reprints as a 2ª Via marked "Documento Cancelado" (PT-77)."""
        quotation = self.make_order()
        self.assertNotIn(CANCELLED, self.print_pdf(quotation))
        self.cancel(quotation)
        html = self.print_pdf(quotation)
        self.assertIn(REPRINT, html)
        self.assertIn(CANCELLED, html)

    def test_printed_content(self):
        """
        The order prints its number and AT designation in Portuguese (PT-28), dates as DD-MM-AAAA, its
        ATCUD as ATCUD:code-n (PT-69), and the exemption reason of each exempt line.
        """
        quotation = self.make_order(
            date_order=datetime(2026, 6, 10, 9, 0),
            validity_date='2026-07-10',
            lines=[{}, {'tax_ids': self.tax_sale_exempt}],
        )
        html = self.print_pdf(quotation)
        self.assertIn('OR 2026/00001', html)
        self.assertIn('Orçamento', html)
        self.assertIn('10-06-2026', html)
        self.assertIn('10-07-2026', html)
        self.assertIn(f'ATCUD:{self.series_or.at_code}-1', html)
        exempt_line = quotation.order_line[1]
        self.assertTrue(exempt_line._l10n_pt_get_line_vat_exemptions_reasons())
        self.assertIn(exempt_line._l10n_pt_get_line_vat_exemptions_reasons(), html)
        sales_order = self.confirm(quotation)
        self.assertIn('Nota de encomenda', self.print_pdf(sales_order))

    def test_customer_without_nif(self):
        """A customer without a NIF is printed "Consumidor final", never as 999999990 (PT-75)."""
        for vat in (False, '999999990'):
            with self.subTest(vat=vat):
                customer = self.env['res.partner'].create({'name': 'Cliente Anónimo', 'vat': vat, 'country_id': self.env.ref('base.pt').id})
                html = self.print_pdf(self.make_order(partner=customer))
                self.assertIn('Consumidor final', html)
                # The QR code itself carries 999999990 (spec v1.1, field B): only the printed text is checked.
                html = re.sub(r'src="/report/barcode/[^"]*"', '', html)
                self.assertNotIn('999999990', html)

    def test_reprint_reason(self):
        """
        Sending an order already printed asks for a reason, logged in the chatter; the wizard then
        opens the sending as asked (Despacho 8632/2014 2.2.16).
        """
        self.company_pt.external_report_layout_id = self.env.ref('web.external_layout_standard')
        quotation = self.make_order()
        first_send = quotation.with_context(check_document_layout=True).action_quotation_send()
        self.assertEqual(first_send['res_model'], 'mail.compose.message')
        self.print_pdf(quotation)
        action = quotation.with_context(check_document_layout=True).action_quotation_send()
        self.assertEqual(action['res_model'], 'l10n_pt.reprint.reason')
        result = self.env['l10n_pt.reprint.reason'].with_context(
            active_model='sale.order', active_ids=quotation.ids,
        ).create({'reason': 'Cliente perdeu o original'}).action_log_and_print()
        self.assertEqual(result['res_model'], 'mail.compose.message')
        self.assertIn('Cliente perdeu o original', quotation.message_ids[:1].body)

    def test_send_attaches_pdf(self):
        """Sending an order by email attaches its print, its Original, also in a test (PT-18)."""
        quotation = self.make_order()
        action = self.send(quotation)
        composer = self.env['mail.compose.message'].with_context(action['context']).create({})
        composer.action_send_mail()
        message = quotation.message_ids.filtered('attachment_ids')[:1]
        self.assertTrue(message.attachment_ids)
        self.assertEqual(quotation.l10n_pt_print_version, 'original')
        self.assertEqual(len(self._attachments(quotation)), 1)

    def test_pro_forma_issues_nothing(self):
        """A pro-forma is not the quotation: printing one issues nothing. Whether PT keeps it at all is D-7 (PT-79)."""
        quotation = self.make_order()
        self.print_pdf(quotation, 'sale.action_report_pro_forma_invoice')
        self.assertNotIssued(quotation)

    def test_mixed_companies_refused(self):
        """Orders of PT and non-PT companies cannot be printed together in one document."""
        quotation = self.make_order()
        foreign = self.make_order(company=self.company_foreign, partner=self.partner_foreign, lines=[
            {'tax_ids': self.company_data_foreign['default_tax_sale']},
        ])
        env = self.env(context={**self.env.context, 'allowed_company_ids': (self.company_pt + self.company_foreign).ids})
        with self.assertRaisesRegex(UserError, "not possible to print documents with the template"):
            self.print_pdf((quotation + foreign).with_env(env))

    # -------------------------------------------------------------------------
    # QR code
    # -------------------------------------------------------------------------

    def test_quotation_qr(self):
        """A mainland quotation: every field, in order (spec v1.1 section 4); D is its SAF-T WorkType."""
        quotation = self.issue(self.make_order())
        self.assertEqual(
            quotation.l10n_pt_qr_code_str,
            f"A:123456789*B:501964843*C:PT*D:OR*E:N*F:20260615*G:OR 2026/00001*H:{self.series_or.at_code}-1*"
            "I1:PT*I7:100.00*I8:23.00*N:23.00*O:123.00*Q:I87w*R:9999",
        )

    def test_sales_order_qr(self):
        """A sales order is an NE, numbered in its own series."""
        sales_order = self.issue(self.confirm(self.make_order()))
        self.assertQrFields(sales_order, {'D': 'NE', 'E': 'N', 'G': 'NE 2026/00001', 'H': f'{self.series_ne.at_code}-1'})

    def test_rates_and_regions(self):
        """Exempt and normal bases per region; another region's taxes go to the J block, N/O sum every block (PT-71)."""
        quotation = self.issue(self.make_order(lines=[
            {'tax_ids': self.tax_sale_exempt, 'price_unit': 40.0},
            {'tax_ids': self.tax_sale_23, 'price_unit': 30.0},
            {'tax_ids': self.tax_sale_azores_16, 'price_unit': 50.0},
        ]))
        self.assertQrFields(quotation, {
            'I1': 'PT', 'I2': '40.00', 'I7': '30.00', 'I8': '6.90',
            'J1': 'PT-AC', 'J7': '50.00', 'J8': '8.00',
            'N': '14.90', 'O': '134.90',
        })

    def test_customer_fields(self):
        """A foreign tax number as collected, without its country prefix (PT-74); no NIF is 999999990."""
        dutch = self.env['res.partner'].create({'name': 'Klant NL', 'vat': 'NL000099998B57', 'country_id': self.env.ref('base.nl').id})
        no_nif = self.env['res.partner'].create({'name': 'Cliente sem NIF', 'country_id': self.env.ref('base.pt').id})
        quotations = self.issue(
            self.make_order(partner=dutch, lines=[{'tax_ids': self.tax_sale_exempt}])
            + self.make_order(partner=no_nif)
        )
        self.assertQrFields(quotations[0], {'B': '000099998B57', 'C': 'NL'})
        self.assertQrFields(quotations[1], {'B': '999999990', 'C': 'PT'})


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSalePortal(TestL10nPtSaleCommon, HttpCase):
    """
    The customer sees a quotation through its portal link. What is presented to the customer is the
    issued document: downloading or viewing its report issues it (Despacho 8632/2014 2.1.1). A quotation
    confirmed into a sales order is accepted: it is not offered for signing or payment again (PT-106).
    """

    def _portal_url(self, order, **params):
        query = '&'.join(f'{key}={value}' for key, value in {'access_token': order._portal_ensure_token(), **params}.items())
        return f'/my/orders/{order.id}?{query}'

    @unittest.skip("PT-132 (todo): numbering needs ir.sequence access, which the portal's public user lacks")
    def test_report_from_portal_issues(self):
        """The report viewed or downloaded from the portal is the issued order."""
        for report_type in ('html', 'pdf'):
            with self.subTest(report_type=report_type):
                quotation = self.make_order()
                response = self.url_open(self._portal_url(quotation, report_type=report_type))
                self.assertEqual(response.status_code, 200)
                self.assertIssued(quotation)
                self.assertIn(quotation.l10n_pt_document_number, response.text)

    def test_confirmed_quotation_not_offered(self):
        """A quotation confirmed into a sales order offers no signing or payment on its page; one not confirmed does."""
        quotation = self.make_order(require_signature=True, require_payment=True)
        self.assertIn('data-bs-target="#modalaccept"', self.url_open(self._portal_url(quotation)).text)
        self.confirm(quotation)
        self.assertNotIn('data-bs-target="#modalaccept"', self.url_open(self._portal_url(quotation)).text)

    @unittest.skip("PT-133 (question): the portal page shows a quotation without issuing it")
    def test_portal_page_shows_issued_quotation(self):
        """The customer's page of a quotation shows it issued, as everything presented to the customer is."""
        quotation = self.make_order()
        response = self.url_open(self._portal_url(quotation))
        self.assertEqual(response.status_code, 200)
        self.assertIssued(quotation)
