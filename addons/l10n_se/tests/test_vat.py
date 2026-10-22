# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from .common import SeAccountTestCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeVat(SeAccountTestCommon):
    """Swedish taxes produce the right boxes of the VAT return (momsdeklaration) with the right sign."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_de = cls.env['res.partner'].create({
            'name': 'Deutsche Kunde GmbH', 'is_company': True,
            'country_id': cls.env.ref('base.de').id, 'vat': 'DE123456788',
        })
        cls.partner_us = cls.env['res.partner'].create({
            'name': 'US Customer Inc', 'is_company': True, 'country_id': cls.env.ref('base.us').id,
        })

    def _box49(self, moves):
        output = sum(self._box(f'se_{n}', moves) for n in ('10', '11', '12', '30', '31', '32', '60', '61', '62'))
        return output - self._box('se_48', moves)

    def test_domestic_sale_and_purchase(self):
        sale = self._invoice('out_invoice', self._tax('sale_tax_25_goods'))
        purchase = self._invoice('in_invoice', self._tax('purchase_tax_25_goods'))
        self.assertEqual(self._box('se_05', sale), 1000)
        self.assertEqual(self._box('se_10', sale), 250)
        self.assertEqual(self._box('se_48', purchase), 250)
        self.assertEqual(self._box49(sale | purchase), 0)
        self.assertEqual(self._box49(sale), 250, "VAT to pay")

    def test_domestic_reverse_charge_construction_12(self):
        """Input VAT on domestic reverse charge is an asset on 2647, not a cost on 4426."""
        bill = self._invoice('in_invoice', self._tax('purchase_construction_services_tax_12_EC'))
        self.assertEqual(self._box('se_24', bill), 1000)
        self.assertEqual(self._box('se_31', bill), 120)
        self.assertEqual(self._box('se_48', bill), 120)
        self.assertEqual(self._box49(bill), 0)
        lines_2647 = bill.line_ids.filtered(lambda line: line.account_id == self._account('2647'))
        self.assertEqual(sum(lines_2647.mapped('balance')), 120)
        self.assertFalse(bill.line_ids.filtered(lambda line: line.account_id.code in ('4426', '4427')))

    def test_goods_reverse_charge_sweden(self):
        bill = self._invoice('in_invoice', self._tax('purchase_goods_tax_25_SE_RC'))
        self.assertEqual(self._box('se_23', bill), 1000)
        self.assertEqual(self._box('se_30', bill), 250)
        self.assertEqual(self._box('se_48', bill), 250)
        self.assertEqual(self._box49(bill), 0)

    def test_import_of_goods(self):
        bill = self._invoice('in_invoice', self._tax('purchase_goods_tax_25_NEC'), partner=self.partner_us)
        self.assertEqual(self._box('se_50', bill), 1000)
        self.assertEqual(self._box('se_60', bill), 250)
        self.assertEqual(self._box('se_48', bill), 250, "import VAT is deductible")
        self.assertEqual(bill.amount_total, 1000)

    def test_triangular_trade(self):
        """The intermediary reports the purchase value in box 37 and the sale value in box 38."""
        purchase = self._invoice('in_invoice', self._tax('triangular_purchase_tax_0_goods'), amount=800, partner=self.partner_de)
        sale = self._invoice('out_invoice', self._tax('triangular_tax_0_goods'), partner=self.partner_de)
        self.assertEqual(self._box('se_37', purchase | sale), 800)
        self.assertEqual(self._box('se_38', purchase | sale), 1000)
        self.assertEqual(self._box49(purchase | sale), 0)
        self.assertIn('Trepartshandel', sale.taxes_legal_notes or '')

    def test_exempt_and_reverse_charge_sales(self):
        exempt = self._invoice('out_invoice', self._tax('sale_tax_0_exempt'))
        reverse_charge = self._invoice('out_invoice', self._tax('sale_tax_0_reverse_charge_SE'))
        self.assertEqual(self._box('se_42', exempt), 1000)
        self.assertEqual(self._box('se_41', reverse_charge), 1000)
        self.assertIn('mervärdesskattelagen', exempt.taxes_legal_notes or '')
        self.assertIn('Omvänd betalningsskyldighet', reverse_charge.taxes_legal_notes or '')

    def test_eu_and_export_sales(self):
        eu = self._invoice('out_invoice', self._tax('sale_tax_goods_EC'), partner=self.partner_de)
        export = self._invoice('out_invoice', self._tax('sale_tax_goods_NEC'), partner=self.partner_us)
        self.assertEqual(self._box('se_35', eu), 1000)
        self.assertEqual(self._box('se_36', export), 1000)
        self.assertEqual(self._box49(eu | export), 0)

    def test_fiscal_positions(self):
        FiscalPosition = self.env['account.fiscal.position']
        sale_25 = self._tax('sale_tax_25_goods')
        cases = [
            (self.partner_se, 'fp_sweden', sale_25, '3011'),
            (self.partner_de, 'fp_euro_b2b', self._tax('sale_tax_goods_EC'), '3106'),
            (self.partner_us, 'fp_outside_euro', self._tax('sale_tax_goods_NEC'), '3105'),
        ]
        for partner, fp_xmlid, expected_tax, expected_account in cases:
            with self.subTest(fiscal_position=fp_xmlid):
                fp = FiscalPosition._get_fiscal_position(partner)
                self.assertEqual(fp, self.env['account.chart.template'].ref(fp_xmlid))
                self.assertEqual(fp.map_tax(sale_25), expected_tax)
                self.assertEqual(fp.map_account(self._account('3011')), self._account(expected_account))
        b2b = self.env['account.chart.template'].ref('fp_euro_b2b')
        self.assertEqual(b2b.map_account(self._account('3012')), self._account('3308'), "services to the EU")

    def test_invoice_f_tax_text(self):
        report = self.env['ir.actions.report']
        invoice = self._invoice('out_invoice', self._tax('sale_tax_25_goods'))
        refund = self._invoice('out_refund', self._tax('sale_tax_25_goods'))
        self.env.company.l10n_se_f_tax_approved = False
        html = report._render_qweb_html('account.report_invoice', invoice.ids)[0].decode()
        self.assertNotIn('Approved for F-tax', html)
        self.env.company.l10n_se_f_tax_approved = True
        for move in (invoice, refund):
            with self.subTest(move_type=move.move_type):
                html = report._render_qweb_html('account.report_invoice', move.ids)[0].decode()
                self.assertIn('Approved for F-tax', html)
