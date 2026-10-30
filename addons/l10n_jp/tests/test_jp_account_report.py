# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

import lxml.html

from odoo.tests import new_test_user, tagged
from odoo.tools import format_date, html2plaintext

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPAccountReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.partner_a.write({
            'lang': 'ja_JP',
            'zip': '100-0005',
            'state_id': cls.env.ref('base.state_jp_jp-13').id,
            'city': '千代田区',
            'street': '丸の内1-1-1',
            'country_id': cls.env.ref('base.jp').id,
        })
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')

    def test_invoice_report_uses_jp_honorific(self):
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            currency_id=self.env.ref('base.JPY'),
            product_id=self.product_a,
            tax_ids=self.tax_sale_a,
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        header = lxml.html.fromstring(html).find_class('o_jp_standard_header')[0].text_content()

        self.assertIn(f'{self.partner_a.name} 様', header)
        self.assertEqual(header.count(self.partner_a.name), 1)

    def test_a_billing_user_prints_the_invoice(self):
        company = self.company_data['company']
        billing_user = new_test_user(
            self.env, login='jp_billing', groups='account.group_account_invoice',
            company_id=company.id, company_ids=company.ids,
        )
        invoice = self._create_invoice_one_line(move_type='out_invoice', partner_id=self.partner_a, product_id=self.product_a, post=True)

        html = self.env['ir.actions.report'].with_user(billing_user)._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        header = lxml.html.fromstring(html).find_class('o_jp_standard_header')[0].text_content()

        self.assertIn(f'{self.partner_a.name} 様', header)

    def test_layout_heads_the_invoice_with_its_date(self):
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            product_id=self.product_a,
            invoice_date='2026-10-01',
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        header = lxml.html.fromstring(html).find_class('o_jp_standard_header')[0].text_content()

        self.assertIn(format_date(self.env, invoice.invoice_date, lang_code='ja_JP'), header)

    def test_every_tax_rate_shows_its_base_and_its_tax(self):
        tax_8 = self.tax_sale_a.copy({
            'name': '8%',
            'amount': 8.0,
            'tax_group_id': self.env['account.chart.template'].ref('l10n_jp_tax_group_8').id,
        })
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_a.id,
            currency_id=self.env.ref('base.JPY').id,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=10000, tax_ids=self.tax_sale_a),
                self._prepare_invoice_line(price_unit=5000, tax_ids=tax_8),
            ],
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)

        self.assertEqual(len(lxml.html.fromstring(html).find_class('o_taxes')), 2)
        self.assertCountEqual(re.findall(r'Taxable Amount\s+¥\s*([\d,]+)', text), ['10,000', '5,000'])
        self.assertCountEqual(re.findall(r'Tax\s+¥\s*([\d,]+)', text), ['1,000', '400'])

    def test_payment_receipt_uses_jp_honorific(self):
        payment = self.init_payment(100.0, partner=self.partner_a, post=True)

        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_payment_receipt', payment.ids)[0]
        document = lxml.html.fromstring(html)

        self.assertIn(f'{self.partner_a.name} 様', document.find_class('o_jp_standard_header')[0].text_content())
        self.assertEqual(document.text_content().count(self.partner_a.name), 1)

    def test_unit_price_column_drops_a_decimal_part_worth_nothing(self):
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

        self.assertEqual(self._get_unit_price_cells(html), ['202', '105'])

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

        self.assertEqual(self._get_unit_price_cells(html), ['202.00', '101.50'])

    def test_unit_price_column_keeps_the_decimals_of_its_currency(self):
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_a,
            currency_id=self.setup_other_currency('USD'),
            invoice_line_ids=[self._prepare_invoice_line(price_unit=202.0, product_id=self.product_a, tax_ids=self.tax_sale_a)],
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]

        self.assertEqual(self._get_unit_price_cells(html), ['202.00'])

    def test_another_layout_keeps_the_name_in_the_address(self):
        self.company_data['company'].external_report_layout_id = self.env.ref('web.external_layout_standard')
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            product_id=self.product_a,
            tax_ids=self.tax_sale_a,
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        address = lxml.html.fromstring(html).find_class('address')[0].text_content()

        self.assertIn(self.partner_a.name, address)
        self.assertIn('Taxable Amount', html2plaintext(html))

    def test_a_company_outside_japan_keeps_the_standard_invoice(self):
        invoice = self._create_invoice_one_line(move_type='out_invoice', partner_id=self.partner_a, product_id=self.product_a, post=True)
        self.assertEqual(invoice._get_name_invoice_report(), 'l10n_jp.report_invoice_document')

        self.company_data['company'].account_fiscal_country_id = self.env.ref('base.us')

        self.assertEqual(invoice._get_name_invoice_report(), 'account.report_invoice_document')

    def test_the_japanese_chart_brings_the_japanese_layout(self):
        company = self.env['res.company'].create({'name': 'JP Company 2', 'country_id': self.env.ref('base.jp').id})
        self.env['account.chart.template'].try_loading('jp', company=company, install_demo=False)

        self.assertEqual(company.external_report_layout_id, self.env.ref('l10n_jp.external_layout_jp_standard'))

    def test_a_contact_comes_under_its_company(self):
        company = self.env['res.partner'].create({'name': 'JP Trading KK', 'lang': 'ja_JP'})
        for contact, lines in (
            (self.env['res.partner'].create({'name': 'Taro Yamada', 'parent_id': company.id}), ['JP Trading KK', 'Taro Yamada 様']),
            # an invoicing address that names nobody is addressed to the company
            (self.env['res.partner'].create({'type': 'invoice', 'parent_id': company.id}), ['JP Trading KK 御中']),
        ):
            with self.subTest(contact=contact.display_name):
                invoice = self._create_invoice_one_line(move_type='out_invoice', partner_id=contact, product_id=self.product_a, post=True)
                html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
                recipient = lxml.html.fromstring(html).find_class('o_jp_standard_header')[0].xpath(".//div[@name='recipient_name']")[0]

                self.assertEqual([' '.join(line.text_content().split()) for line in recipient], lines)

    def test_only_a_japanese_reader_gets_an_honorific(self):
        self.partner_b.lang = 'en_US'
        invoice = self._create_invoice_one_line(move_type='out_invoice', partner_id=self.partner_b, product_id=self.product_a, post=True)
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        header = lxml.html.fromstring(html).find_class('o_jp_standard_header')[0].text_content()

        self.assertIn(self.partner_b.name, header)
        self.assertNotIn('様', header)
        self.assertNotIn('御中', header)

    def test_layout_prints_a_document_without_partner(self):
        # e.g. a batch transfer, or the return label of the customer portal
        html = self.env['ir.actions.report']._render_template('web.external_layout', {'o': None})

        self.assertIn(self.company_data['company'].name, html2plaintext(html))

    def _get_unit_price_cells(self, html):
        return [cell.text_content().strip() for cell in lxml.html.fromstring(html).xpath("//td[@name='td_price_unit']")]
