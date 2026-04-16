from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

from odoo.addons.sale.tests.common import SaleCommon


@tagged("-at_install", "post_install")
class TestSaleReportCurrencyRate(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.usd_cmp = cls.env["res.company"].create({
            "name": "USD Company",
            "currency_id": cls.env.ref("base.USD").id,
        })
        cls.eur_cmp = cls.env["res.company"].create({
            "name": "EUR Company",
            "currency_id": cls.env.ref("base.EUR").id,
        })

    def test_sale_report_with_downpayment(self):
        """Check that downpayment lines are used in the calculation of amounts invoiced and to
        invoice."""
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": self.product.id})],
        })
        order.action_confirm()

        downpayment = (
            self
            .env["sale.advance.payment.inv"]
            .with_context(active_ids=order.ids)
            .create({"advance_payment_method": "fixed", "fixed_amount": 200})
        )
        downpayment.create_invoices()
        order.invoice_ids.action_post()
        order.order_line.flush_recordset()

        amount_line = self.env["sale.report"].formatted_read_group(
            [("order_reference", "=", f"sale.order,{order.id}")],
            aggregates=["untaxed_amount_to_invoice:sum", "untaxed_amount_invoiced:sum"],
        )[0]

        self.assertEqual(
            float_compare(
                amount_line["untaxed_amount_invoiced:sum"],
                200,
                precision_rounding=order.currency_id.rounding,
            ),
            0,
        )
        self.assertEqual(
            float_compare(
                amount_line["untaxed_amount_to_invoice:sum"],
                self.product.lst_price - 200,
                precision_rounding=order.currency_id.rounding,
            ),
            0,
        )
