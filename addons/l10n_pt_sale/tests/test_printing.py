import re
from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from odoo.addons.l10n_pt_certification.tests.test_printing import CANCELLED, ORIGINAL, REPRINT
from odoo.addons.l10n_pt_sale.tests.common import SIGNATURE, TestL10nPtSaleCommon

DRAFT_WARNING = 'l10n_pt_draft_notice'
SALES_ORDER_NOTICE = 'id="l10n_pt_sales_order_notice"'
REPORT_BUTTON = 'id="print_invoice_report"'


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
        """The first print of an order is its Original, the next its 2ª Via, each stored."""
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
        """A cancelled order reprints as a 2ª Via marked "Documento Cancelado"."""
        quotation = self.make_order()
        self.assertNotIn(CANCELLED, self.print_pdf(quotation))
        self.cancel(quotation)
        html = self.print_pdf(quotation)
        self.assertIn(REPRINT, html)
        self.assertIn(CANCELLED, html)

    def test_printed_content(self):
        """
        The order prints its number and AT designation in Portuguese, dates as DD-MM-AAAA, its
        ATCUD as ATCUD:code-n, and the exemption reason of each exempt line.
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
        """A customer without a NIF is printed "Consumidor final", never as 999999990."""
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
        """Sending an order by email attaches its print, its Original, also in a test."""
        quotation = self.make_order()
        action = self.send(quotation)
        composer = self.env['mail.compose.message'].with_context(action['context']).create({})
        composer.action_send_mail()
        message = quotation.message_ids.filtered('attachment_ids')[:1]
        self.assertTrue(message.attachment_ids)
        self.assertEqual(quotation.l10n_pt_print_version, 'original')
        self.assertEqual(len(self._attachments(quotation)), 1)

    def test_pro_forma_issues_nothing(self):
        """A pro-forma is not the quotation: printing one issues nothing."""
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
        """Exempt and normal bases per region; another region's taxes go to the J block, N/O sum every block."""
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
        """A foreign tax number as collected, without its country prefix; no NIF is 999999990."""
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
    The customer sees a quotation through its portal link. Only an internal user issues a quotation, by
    sending, sharing or printing it: the customer's page and reports never do. One reached
    unissued anyway shows no report, which is refused: no unsigned document is printed (Despacho
    8632/2014 2.2.1); no draft warning is shown. A quotation confirmed into a sales order
    is accepted: it is not offered for signing or payment again.
    """

    def _portal_url(self, order, **params):
        query = '&'.join(f'{key}={value}' for key, value in {'access_token': order._portal_ensure_token(), **params}.items())
        return f'/my/orders/{order.id}?{query}'

    def test_report_from_portal(self):
        """
        The customer's report of an issued quotation is the issued document; of one not issued yet, it is
        refused, and the customer sent back to its page.
        """
        quotation = self.make_order()
        for report_type in ('html', 'pdf'):
            with self.subTest(report_type=report_type, issued=False):
                response = self.url_open(self._portal_url(quotation, report_type=report_type), allow_redirects=False)
                self.assertIn(response.status_code, (302, 303))
                self.assertIn(f'/my/orders/{quotation.id}', response.headers['Location'])
                self.assertNotIn('report_type', response.headers['Location'])
                self.assertNotIssued(quotation)
        self.issue(quotation)
        for report_type in ('html', 'pdf'):
            with self.subTest(report_type=report_type, issued=True):
                response = self.url_open(self._portal_url(quotation, report_type=report_type))
                self.assertEqual(response.status_code, 200)
                self.assertIn(quotation.l10n_pt_document_number, response.text)

    def test_confirmed_quotation_not_offered(self):
        """An issued quotation confirmed into a sales order offers no signing or payment on its page; one not confirmed does."""
        quotation = self.issue(self.make_order(require_signature=True, require_payment=True))
        self.assertIn('data-bs-target="#modalaccept"', self.url_open(self._portal_url(quotation)).text)
        self.confirm(quotation)
        self.assertNotIn('data-bs-target="#modalaccept"', self.url_open(self._portal_url(quotation)).text)

    def test_portal_page_does_not_issue(self):
        """
        The customer's page of a quotation never issues it. One not issued yet -- e.g. the link
        of a Preview copied by the salesperson -- is shown without its report, and with no draft warning;
        an issued one with its report.
        """
        quotation = self.make_order()
        response = self.url_open(self._portal_url(quotation))
        self.assertEqual(response.status_code, 200)
        self.assertNotIssued(quotation)
        self.assertNotIn(DRAFT_WARNING, response.text)
        self.assertNotIn(REPORT_BUTTON, response.text)
        self.issue(quotation)
        response = self.url_open(self._portal_url(quotation))
        self.assertIn(REPORT_BUTTON, response.text)

    def test_accept_lands_on_sales_order(self):
        """
        The customer who signs an issued quotation, with no payment due, lands on the sales order
        confirmed from it, which says the order is confirmed.
        """
        quotation = self.issue(self.make_order(require_signature=True, require_payment=False))
        # Without its confirmation mail, which fails to render as the public user over HTTP in this
        # class; the in-process acceptance tests send it.
        with patch.object(self.registry['sale.order'], '_send_order_confirmation_mail', lambda orders: None):
            result = self.make_jsonrpc_request(f'/my/orders/{quotation.id}/accept', {
                'access_token': quotation._portal_ensure_token(),
                'name': "Cliente PT",
                'signature': SIGNATURE,
            })
        sales_order = quotation.sales_order_ids
        self.assertEqual(len(sales_order), 1)
        self.assertTrue(result['redirect_url'].startswith(f'/my/orders/{sales_order.id}?'), result['redirect_url'])
        self.assertIn('message=sign_ok', result['redirect_url'])
        self.assertIn("Your order has been confirmed.", self.url_open(result['redirect_url']).text)

    def test_quotation_page_links_sales_order(self):
        """The page of a quotation confirmed into a sales order says so and links to the sales order."""
        quotation = self.issue(self.make_order())
        page = self.url_open(self._portal_url(quotation)).text
        self.assertNotIn(SALES_ORDER_NOTICE, page)
        sales_order = self.confirm(quotation)
        page = self.url_open(self._portal_url(quotation)).text
        self.assertIn(SALES_ORDER_NOTICE, page)
        self.assertIn(f'/my/orders/{sales_order.id}?access_token=', page)

    def test_customer_declines_issued_quotation(self):
        """
        A customer declining an issued quotation on its page, with a message, cancels it with that
        message as its reason (Portaria 302/2016 4.3.4.3.3), recorded under its salesperson:
        no person cancels it there.
        """
        quotation = self.issue(self.make_order(require_signature=True, require_payment=False))
        page = self.url_open(self._portal_url(quotation)).text
        csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        response = self.url_open(f'/my/orders/{quotation.id}/decline', data={
            'access_token': quotation._portal_ensure_token(),
            'decline_message': "  Preço acima do previsto  ",
            'csrf_token': csrf_token,
        })
        self.assertEqual(response.status_code, 200)
        quotation.invalidate_recordset()
        self.assertRecordValues(quotation, [{
            'state': 'cancel',
            'l10n_pt_cancel_reason': "Preço acima do previsto",
            'l10n_pt_cancel_user_id': self.salesman.id,
            'l10n_pt_document_number': 'OR 2026/00001',
        }])
        self.assertTrue(quotation.l10n_pt_cancel_date)

    def test_salesperson_preview_does_not_issue(self):
        """
        A salesperson looking at the portal page of a quotation -- the form's Preview -- issues nothing,
        and sees no draft warning.
        """
        quotation = self.make_order()
        self.authenticate(self.salesman.login, self.salesman.login)
        response = self.url_open(self._portal_url(quotation))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(DRAFT_WARNING, response.text)
        # Printing it from there is the salesperson's print, which issues it.
        self.assertIn(REPORT_BUTTON, response.text)
        self.assertNotIssued(quotation)
