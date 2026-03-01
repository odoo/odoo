from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# FBR reads invoiceTime as Pakistan Standard Time (UTC+5, no DST), so the tests freeze a
# UTC instant and expect the payload to report the Karachi wall clock five hours later.
FROZEN_UTC = '2026-06-02 04:30:00'
FROZEN_PKT_TIME = '09:30:00'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPkEdiPayload(AccountTestInvoicingCommon):
    """Cover the FBR JSON payload built by _get_l10n_pk_edi_line_details and
    _l10n_pk_edi_generate_invoice_json, against FBR's own sandbox scenarios."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pk')
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.company_data['company']
        cls.company.write({
            'vat': '4174942',
            'street': 'Plot 1 Block A SITE Area',
            'city': 'Karachi',
            'state_id': cls.env.ref('base.state_pk_sd').id,
            'country_id': cls.env.ref('base.pk').id,
        })

        cls.partner_pk = cls.env['res.partner'].create({
            'name': 'Jalal LLC Pakistan',
            'vat': '1234567-8',
            'street': 'Street 1 Street 2',
            'city': 'Karachi',
            'state_id': cls.env.ref('base.state_pk_sd').id,
            'country_id': cls.env.ref('base.pk').id,
            'l10n_pk_edi_fbr_customer_status': 'registered',
        })

        cls.tax_gst_18 = cls.env['account.chart.template'].ref('pk_sales_tax_gst_18')
        cls.tax_gst_18_3rd = cls.env['account.chart.template'].ref('pk_sales_tax_gst_18_3rd')
        cls.tax_gst_ft_4 = cls.env['account.chart.template'].ref('pk_sales_tax_gst_ft_4')
        cls.tax_swht = cls.env['account.chart.template'].ref('pk_sales_tax_swht_1_10th')
        cls.tax_sales_0 = cls.env['account.chart.template'].ref('pk_sales_tax_0')
        cls.tax_gst_5_rr = cls.env['account.chart.template'].ref('pk_sales_tax_gst_5_rr')

        # 'Numbers, pieces, units' is the FBR UoM code carried by uom.product_uom_unit.
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')

    @classmethod
    def _create_pk_product(cls, name, list_price, sale_type='75'):
        return cls._create_product(
            name=name,
            list_price=list_price,
            uom_id=cls.uom_unit,
            hs_code='01012100',
            l10n_pk_edi_sale_type=sale_type,
        )

    @classmethod
    def _create_pk_invoice(cls, product, tax, price_unit, quantity=1.0, discount=0.0, uom=None):
        return cls._create_invoice(
            partner_id=cls.partner_pk,
            invoice_date='2026-06-02',
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    product_id=product,
                    product_uom_id=uom or product.uom_id,
                    price_unit=price_unit,
                    quantity=quantity,
                    discount=discount,
                    tax_ids=tax,
                ),
            ],
            post=True,
        )

    def _render_invoice_report(self, invoice):
        report, _ = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)
        return report.decode()

    def _create_debit_note(self, origin_status='sent', reference='SN001-INV-001'):
        """A debit note raised against an invoice FBR has already accepted."""
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        origin = self._create_pk_invoice(product, self.tax_gst_18, price_unit=100.0)
        origin.write({
            'l10n_pk_edi_status': origin_status,
            'l10n_pk_edi_reference': reference,
        })
        # The wizard carries its reason over to l10n_pk_edi_refund_reason for PK companies.
        self.env['account.debit.note'].with_context(
            active_model='account.move', active_ids=origin.ids,
        ).create({'reason': 'Goods returned', 'copy_lines': True}).create_debit()
        debit_note = origin.debit_note_ids
        debit_note.action_post()
        return debit_note

    # -------------------------------------------------------------------------
    # _get_l10n_pk_edi_line_details
    # -------------------------------------------------------------------------

    def test_line_details_standard_rated(self):
        """A plain 18% line reports the nominal rate on the invoiced amount."""
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        invoice = self._create_pk_invoice(product, self.tax_gst_18, price_unit=100.0)

        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['rate'], '18%')
        self.assertEqual(line_vals['valueSalesExcludingST'], 100.0)
        self.assertEqual(line_vals['salesTaxApplicable'], 18.0)
        self.assertEqual(line_vals['totalValues'], 118.0)
        self.assertEqual(line_vals['furtherTax'], 0.0)
        # Only 3rd Schedule lines report a notified retail price.
        self.assertEqual(line_vals['fixedNotifiedValueOrRetailPrice'], "")
        self.assertEqual(line_vals['saleType'], 'Goods at standard rate (default)')

    def test_line_details_third_schedule(self):
        """FBR scenario SN027: tax follows the retail price, reported net of itself."""
        # GST 18% 3rd is price_include_override='tax_included', so price_unit carries the tax.
        product = self._create_pk_product('Soap', list_price=118.0, sale_type='23')
        invoice = self._create_pk_invoice(product, self.tax_gst_18_3rd, price_unit=118.0)

        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['rate'], '18%')
        self.assertEqual(line_vals['fixedNotifiedValueOrRetailPrice'], 100.0)
        self.assertEqual(line_vals['salesTaxApplicable'], 18.0)
        self.assertEqual(line_vals['valueSalesExcludingST'], 100.0)
        self.assertEqual(line_vals['totalValues'], 118.0)
        self.assertEqual(line_vals['saleType'], '3rd Schedule Goods')

    def test_line_details_third_schedule_discounted(self):
        """FBR scenario SN008: sold below retail, the tax still follows the retail price."""
        product = self._create_pk_product('Shampoo', list_price=118.0, sale_type='23')
        invoice = self._create_pk_invoice(product, self.tax_gst_18_3rd, price_unit=90.0)

        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['rate'], '18%')
        self.assertEqual(line_vals['fixedNotifiedValueOrRetailPrice'], 100.0)
        self.assertEqual(line_vals['salesTaxApplicable'], 18.0)
        self.assertEqual(line_vals['valueSalesExcludingST'], 72.0)
        self.assertEqual(line_vals['totalValues'], 90.0)

    def test_line_details_third_schedule_scales_with_quantity(self):
        """The notified retail price is per-unit retail times quantity, not the gross."""
        product = self._create_pk_product('Soap', list_price=118.0, sale_type='23')
        invoice = self._create_pk_invoice(product, self.tax_gst_18_3rd, price_unit=118.0, quantity=3.0)

        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['rate'], '18%')
        self.assertEqual(line_vals['fixedNotifiedValueOrRetailPrice'], 300.0)
        self.assertEqual(line_vals['salesTaxApplicable'], 54.0)

    def test_line_details_further_and_withheld_tax(self):
        """FBR scenario SN002: further tax and withholding sit apart from the sales tax."""
        product = self._create_pk_product('Furniture', list_price=100.0)
        invoice = self._create_pk_invoice(
            product, self.tax_gst_18 | self.tax_gst_ft_4, price_unit=100.0,
        )

        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['salesTaxApplicable'], 18.0)
        self.assertEqual(line_vals['furtherTax'], 4.0)
        self.assertEqual(line_vals['salesTaxWithheldAtSource'], 0.0)
        self.assertEqual(line_vals['valueSalesExcludingST'], 100.0)
        self.assertEqual(line_vals['totalValues'], 122.0)

        # SWHT (1/10th) is -10% on the chart template and is kept out of the ordinary tax
        # computation, so this only reports a value while the base line opts in.
        invoice = self._create_pk_invoice(
            product, self.tax_gst_18 | self.tax_swht, price_unit=100.0,
        )

        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['salesTaxWithheldAtSource'], 10.0)
        self.assertEqual(line_vals['salesTaxApplicable'], 18.0)
        self.assertEqual(line_vals['furtherTax'], 0.0)
        self.assertEqual(line_vals['rate'], '18%')

    def test_line_details_rate(self):
        """Every sales tax rate on the line is listed, unless the sale type carries a tag."""
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        exempt_product = self._create_pk_product('Wheat Flour', list_price=100.0, sale_type='81')
        cases = (
            (product, self.tax_gst_18 | self.tax_gst_5_rr, '18%,5%', 23.0),
            # Further tax and withholding are reported in their own keys, not in the rate.
            (product, self.tax_gst_18 | self.tax_gst_ft_4, '18%', 18.0),
            # An exempt line reports its tag whether or not a 0% tax is set on it.
            (exempt_product, self.tax_sales_0, 'Exempt', 0.0),
            (exempt_product, self.env['account.tax'], 'Exempt', 0.0),
        )
        for line_product, tax, expected_rate, expected_tax_amount in cases:
            with self.subTest(rate=expected_rate, tax=', '.join(tax.mapped('name')) or 'no tax'):
                invoice = self._create_pk_invoice(line_product, tax, price_unit=100.0)

                line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
                self.assertEqual(line_vals['rate'], expected_rate)
                # The rates are listed apart, but the amount stays a single total for the line.
                self.assertEqual(line_vals['salesTaxApplicable'], expected_tax_amount)
                self.assertEqual(line_vals['valueSalesExcludingST'], 100.0)

    def test_line_details_uom(self):
        """The quantity is expressed in the line's unit, so the code must come from it."""
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        invoice = self._create_pk_invoice(
            product, self.tax_gst_18, price_unit=100.0, quantity=2.0, uom=self.uom_dozen,
        )

        # The product's own unit is Units, while the line sells Dozens.
        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['uoM'], 'Dozen')
        self.assertEqual(line_vals['quantity'], 2.0)

        # A unit with no FBR code falls back to one FBR defines, not a made-up string.
        self.uom_dozen.l10n_pk_edi_uom_code = False
        line_vals = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)[0]
        self.assertEqual(line_vals['uoM'], 'Others')

    def test_line_details_skips_non_product_lines(self):
        """Sections and notes carry no taxable base and must not reach the payload."""
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        invoice = self._create_pk_invoice(product, self.tax_gst_18, price_unit=100.0)
        invoice.button_draft()
        invoice.write({
            'invoice_line_ids': [
                Command.create({'display_type': 'line_section', 'name': 'Section'}),
                Command.create({'display_type': 'line_note', 'name': 'Note'}),
            ],
        })
        invoice.action_post()

        line_details = invoice._get_l10n_pk_edi_line_details(invoice.invoice_line_ids)
        self.assertEqual(len(line_details), 1)
        self.assertEqual(line_details[0]['productDescription'], 'Ceiling Fan')

    # -------------------------------------------------------------------------
    # _l10n_pk_edi_generate_invoice_json
    # -------------------------------------------------------------------------

    @freeze_time(FROZEN_UTC)
    def test_generate_invoice_json(self):
        """The envelope carries seller, buyer, the Karachi clock and the line items."""
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        invoice = self._create_pk_invoice(product, self.tax_gst_18, price_unit=100.0)

        payload = invoice._l10n_pk_edi_generate_invoice_json()
        self.assertEqual(payload['invoiceType'], 'Sale Invoice')
        self.assertEqual(payload['invoiceDate'], '2026-06-02')
        self.assertEqual(payload['invoiceTime'], FROZEN_PKT_TIME)
        self.assertEqual(payload['invoiceRefNo'], invoice.name)
        self.assertEqual(payload['sellerNTNCNIC'], '4174942')
        self.assertEqual(payload['sellerProvince'], 'SINDH')
        self.assertEqual(payload['buyerNTNCNIC'], '12345678')
        self.assertEqual(payload['buyerProvince'], 'SINDH')
        self.assertEqual(payload['buyerRegistrationType'], 'Registered')
        self.assertEqual(payload['invoiceTotalAmount'], invoice.amount_total)
        self.assertEqual(len(payload['items']), 1)
        # scenarioId is sandbox-only and must not leak into a production payload.
        self.assertNotIn('scenarioId', payload)

        # The clock is Karachi's whatever the server or the user runs on: a UTC evening is
        # already the next morning there, while the date stays the invoice's own.
        self.env.user.tz = 'America/New_York'
        with freeze_time('2026-06-02 20:30:00'):
            payload = invoice._l10n_pk_edi_generate_invoice_json()
        self.assertEqual(payload['invoiceTime'], '01:30:00')
        self.assertEqual(payload['invoiceDate'], '2026-06-02')

    def test_generate_invoice_json_unregistered_buyer(self):
        """An unregistered buyer is reported with the FBR placeholder identifier."""
        self.partner_pk.l10n_pk_edi_fbr_customer_status = 'unregistered'
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        invoice = self._create_pk_invoice(product, self.tax_gst_18, price_unit=100.0)

        payload = invoice._l10n_pk_edi_generate_invoice_json()
        self.assertEqual(payload['buyerNTNCNIC'], '0000000')
        self.assertEqual(payload['buyerRegistrationType'], 'Unregistered')

    def test_generate_invoice_json_scenario_id_in_test_mode(self):
        """In sandbox mode the configured scenario id rides along on any invoice."""
        self.env['ir.config_parameter'].sudo().set_str('l10n_pk_edi.test_scenario_id', 'SN027')
        product = self._create_pk_product('Soap', list_price=118.0, sale_type='23')
        invoice = self._create_pk_invoice(product, self.tax_gst_18_3rd, price_unit=118.0)

        self.env['ir.config_parameter'].sudo().set_str('l10n_pk_edi.mode', 'test')
        payload = invoice._l10n_pk_edi_generate_invoice_json()
        self.assertEqual(payload['scenarioId'], 'SN027')

    @freeze_time(FROZEN_UTC)
    def test_generate_invoice_json_debit_note(self):
        """A debit note points FBR at the reference of the invoice it corrects."""
        payload = self._create_debit_note()._l10n_pk_edi_generate_invoice_json()
        self.assertEqual(payload['invoiceType'], 'Debit Note')
        self.assertEqual(payload['invoiceRefNo'], 'SN001-INV-001')
        self.assertEqual(payload['reason'], 'Goods returned')

        self.env['ir.config_parameter'].sudo().set_str('l10n_pk_edi.mode', 'test')

        sandbox = self._create_debit_note(origin_status='sent_test')._l10n_pk_edi_generate_invoice_json()
        unreferenced = self._create_debit_note(origin_status='sent_test', reference=False)._l10n_pk_edi_generate_invoice_json()

        # The FBR sandbox rejects a reference it has already seen, hence the suffix.
        self.assertEqual(sandbox['invoiceRefNo'], 'SN001-INV-001*test*')
        self.assertEqual(sandbox['reason'], 'Goods returned')
        # An origin marked sent but carrying no reference must not break the payload.
        self.assertEqual(unreferenced['invoiceRefNo'], '')

    # -------------------------------------------------------------------------
    # Invoice report
    # -------------------------------------------------------------------------

    def test_report_prints_fbr_qr_code_and_logo(self):
        """The FBR artwork is compliance, not payment: the bank QR settings must not gate it."""
        # display_qr_code follows company.qr_code, and the payment QR block also needs an open
        # balance; neither has any bearing on what FBR requires on the invoice.
        self.company.qr_code = False
        product = self._create_pk_product('Ceiling Fan', list_price=100.0)
        invoice = self._create_pk_invoice(product, self.tax_gst_18, price_unit=100.0)
        self.assertFalse(invoice.display_qr_code)

        # _get_name_invoice_report only routes to the PK template for an enabled PK company.
        self.company.l10n_pk_edi_enable = True
        self.assertEqual(invoice._get_name_invoice_report(), 'l10n_pk_edi.report_invoice_document')

        invoice.l10n_pk_edi_reference = 'SN001-INV-001'
        report = self._render_invoice_report(invoice)
        self.assertIn('logo_fbr', report)
        self.assertIn('img_fbr_einvoice.png', report)
        self.assertIn('data:image/png;base64', report)
        self.assertIn('SN001-INV-001', report)
