from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestSaleDownpaymentFiscalPosition(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env['account.account']
        cls.acc_down_dom = Account.create({
            'code': 'TEST4600', 'name': 'Downpayment', 'account_type': 'liability_current'})
        cls.acc_down_exp = Account.create({
            'code': 'TEST4601', 'name': 'Export Downpayment', 'account_type': 'liability_current'})
        cls.env.company.downpayment_account_id = cls.acc_down_dom
        cls.fiscal_position = cls.env['account.fiscal.position'].create({
            'name': 'Export Mapping',
            'account_ids': [Command.create({
                'account_src_id': cls.acc_down_dom.id,
                'account_dest_id': cls.acc_down_exp.id,
            })],
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Export Customer',
            'property_account_position_id': cls.fiscal_position.id,
        })

    def test_downpayment_account_mapped_by_fiscal_position(self):
        """The company downpayment account is mapped by the order's fiscal position."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fiscal_position.id,
            'order_line': [Command.create({
                'name': 'test', 'price_unit': 1000.0, 'product_uom_qty': 1.0,
            })],
        })
        sale_order.action_confirm()
        self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order', active_ids=sale_order.ids, active_id=sale_order.id,
        ).create({'advance_payment_method': 'percentage', 'amount': 10.0}).create_invoices()

        invoice = sale_order.invoice_ids
        self.assertTrue(invoice, "The downpayment invoice was not created.")
        dp_line = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertEqual(dp_line.account_id, self.acc_down_exp)
