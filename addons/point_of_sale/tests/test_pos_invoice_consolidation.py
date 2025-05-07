from odoo import Command
from odoo.addons.point_of_sale.tests.common import CommonPosTest, TestPoSCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestPosInvoiceConsolidation(TestPoSCommon, CommonPosTest):

    def setUp(cls):
        super().setUp()
        cls.config = cls.basic_config
        cls.user1 = cls.env.user
        cls.user2 = cls.simple_accountman
        cls.user2.group_ids = [Command.link(cls.env.ref('point_of_sale.group_pos_user').id)]
        cls.product1 = cls.create_product('Product 1', cls.categ_basic, 10.0)
        cls.product2 = cls.create_product('Product 2', cls.categ_basic, 20.0)

    def test_invoice_grouped_by_user_id(self):
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders_user1 = self._create_orders([{
                'pos_order_lines_ui_args': [(self.product1, 1)],
                'customer': self.customer,
                'is_invoiced': False,
                'uuid': 'u1-order',
            }])
            # This flattens the dict into the recordset
            orders_user1 = sum(orders_user1.values(), self.env['pos.order'])

        with self.with_user(self.user2.login):
            orders_user2 = self._create_orders([
                {
                    'pos_order_lines_ui_args': [(self.product1, 2)],
                    'customer': self.customer,
                    'is_invoiced': False,
                }, {
                    'pos_order_lines_ui_args': [(self.product2, 1)],
                    'customer': self.customer,
                    'is_invoiced': False,
                }
            ])
            # This flattens the dict into the recordset
            orders_user2 = sum(orders_user2.values(), self.env['pos.order'])

        all_orders = orders_user1 + orders_user2

        # create consolidated invoice
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=all_orders.ids).action_create_invoices()

        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 1, "User 2 should have one invoice")
        self.assertEqual(sum(orders_user2.mapped('amount_total')), invoice_user2.amount_total)
