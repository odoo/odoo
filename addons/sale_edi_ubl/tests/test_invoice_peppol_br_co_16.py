# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestInvoicePeppolBRCO16(TestUblBis3Common, TestUblCiiBECommon):
    """
    Regression test for Peppol rule BR-CO-16 on BIS3 invoices generated from a
    sale order with a global discount applied.

    BR-CO-16:
        PayableAmount (BT-115) = TaxInclusiveAmount (BT-112)
                               - PrepaidAmount (BT-113)
                               + PayableRoundingAmount (BT-114)

    The invoice export previously derived PayableRoundingAmount from an
    independent base-lines aggregation, which could diverge by one cent from
    invoice.amount_total when the tax-smoothing engine applied (e.g. global
    discount landing on an exact rounded target). The fix anchors
    PayableRoundingAmount to invoice.amount_total so BR-CO-16 holds by
    construction.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ensure_installed('sale')
        cls.ubl_namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

    def _assert_br_co_16(self, invoice):
        self.assertTrue(invoice.ubl_cii_xml_id)
        tree = etree.fromstring(invoice.ubl_cii_xml_id.raw)

        def _get_amount(xpath):
            node = tree.find(xpath, self.ubl_namespaces)
            return float(node.text) if node is not None and node.text else 0.0

        tax_inclusive = _get_amount('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount')
        prepaid = _get_amount('.//cac:LegalMonetaryTotal/cbc:PrepaidAmount')
        rounding = _get_amount('.//cac:LegalMonetaryTotal/cbc:PayableRoundingAmount')
        payable = _get_amount('.//cac:LegalMonetaryTotal/cbc:PayableAmount')
        self.assertEqual(
            payable,
            tax_inclusive - prepaid + rounding,
            msg=(
                f"BR-CO-16 violated: PayableAmount={payable} != "
                f"TaxInclusive({tax_inclusive}) - Prepaid({prepaid}) "
                f"+ Rounding({rounding})"
            ),
        )

    def _build_sale_order(self, tax):
        return self.env['sale.order'].sudo().create({
            'partner_id': self.partner_be.id,
            'order_line': [
                Command.create({
                    'name': f'Line {i}',
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': price,
                    'tax_ids': [Command.set(tax.ids)],
                }) for i, price in enumerate((97.59, 95.34, 88.21), start=1)
            ],
        })

    def _invoice_and_export(self, sale_order):
        invoice = sale_order._create_invoices()
        invoice.action_post()
        self._generate_invoice_ubl_file(invoice)
        return invoice

    def test_br_co_16_global_discount_round_per_tax(self):
        """Test BR-CO-16 compliance when using 'Round Globally' with a global discount.
        Ensures that the 1-cent adjustment from the tax-smoothing engine is correctly
        reflected in the UBL PayableRoundingAmount."""
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax_21 = self.percent_tax(21.0)
        so = self._build_sale_order(tax_21)
        self.env['sale.order.discount'].sudo().create({
            'sale_order_id': so.id,
            'discount_type': 'so_discount',
            'discount_percentage': 0.03,
        }).action_apply_discount()
        so.action_confirm()
        invoice = self._invoice_and_export(so)
        self._assert_br_co_16(invoice)

    def test_br_co_16_global_discount_round_per_line(self):
        """Test BR-CO-16 compliance when using 'Round per Line' with a global discount.
        Verifies that even with per-line rounding, any global discount smoothing is
        accurately balanced by the UBL rounding amount."""
        self.env.company.tax_calculation_rounding_method = 'round_per_line'
        tax_21 = self.percent_tax(21.0)
        so = self._build_sale_order(tax_21)
        self.env['sale.order.discount'].sudo().create({
            'sale_order_id': so.id,
            'discount_type': 'so_discount',
            'discount_percentage': 0.03,
        }).action_apply_discount()
        so.action_confirm()
        invoice = self._invoice_and_export(so)
        self._assert_br_co_16(invoice)
