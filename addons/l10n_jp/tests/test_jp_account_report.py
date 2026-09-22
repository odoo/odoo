# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPAccountReport(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.partner_a.lang = 'ja_JP'
        cls.env.ref('base.JPY').active = True
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')
        # l10n_din5008 rewrites the unit price cell to the monetary widget for
        # every company rather than for its own layout, and it inherits the
        # report after us, so on a database holding it the cell is never ours.
        # These tests are about what the JP rule decides, not about which
        # module ends up styling the cell.
        cls.env['ir.ui.view'].search([('key', '=', 'l10n_din5008.report_invoice_document')]).active = False

    def test_invoice_report_uses_jp_honorific_and_currency_header(self):
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            currency_id=self.env.ref('base.JPY'),
            product_id=self.product_a,
            tax_ids=self.tax_sale_a,
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)
        self.assertIn('Unit Price (円)', text)
        self.assertIn('Amount (円)', text)
        self.assertIn('対象額', text)

    def test_payment_receipt_uses_jp_honorific(self):
        payment = self.init_payment(100.0, partner=self.partner_a, post=True)

        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_payment_receipt', payment.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)

    def test_unit_price_column_drops_a_decimal_part_worth_nothing(self):
        # Two of each line, so that a unit price cannot hide inside its own subtotal.
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_a,
            currency_id=self.env.ref('base.JPY'),
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=202.0, quantity=2.0, product_id=self.product_a, tax_ids=self.tax_sale_a),
                self._prepare_invoice_line(price_unit=105.0, quantity=2.0, product_id=self.product_a, tax_ids=self.tax_sale_a),
            ],
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)

        self.assertIn('202', text)
        self.assertNotIn('202.00', text)
        self.assertIn('105', text)
        self.assertNotIn('105.00', text)

    def test_unit_price_column_keeps_its_decimals_for_one_line_that_needs_them(self):
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_a,
            currency_id=self.env.ref('base.JPY'),
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=202.0, quantity=2.0, product_id=self.product_a, tax_ids=self.tax_sale_a),
                self._prepare_invoice_line(price_unit=101.5, quantity=2.0, product_id=self.product_a, tax_ids=self.tax_sale_a),
            ],
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)

        self.assertIn('202.00', text)
        self.assertIn('101.50', text)

    def test_the_column_decides_for_every_price_in_it(self):
        company = self.company_data['company']

        self.assertTrue(company._l10n_jp_hide_zero_decimals([202.0, 105.0]))
        self.assertFalse(company._l10n_jp_hide_zero_decimals([202.0, 101.5]))

    def test_the_rule_is_for_a_japanese_company_only(self):
        company = self.company_data['company']
        company.account_fiscal_country_id = self.env.ref('base.us')

        self.assertFalse(company._l10n_jp_hide_zero_decimals([202.0, 105.0]))
