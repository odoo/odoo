# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestPosOrderLineTaxes(TestPoSCommon):
    """ Taxes after fiscal position on pos order lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

        cls.fpos = cls.env['account.fiscal.position'].create({'name': 'FP'})
        cls.fpos_other = cls.env['account.fiscal.position'].create({'name': 'FP other'})
        cls.tax_10, cls.tax_15, cls.tax_20, cls.tax_25, cls.tax_other = cls.env['account.tax'].create([
            {'name': f'Tax {amount}', 'type_tax_use': 'sale', 'amount_type': 'percent', 'amount': amount}
            for amount in (10, 15, 20, 25, 30)
        ])
        # FP maps 10% -> 20%, the 'other' tax is restricted to another fiscal position
        cls.tax_20.write({
            'fiscal_position_ids': [Command.link(cls.fpos.id)],
            'original_tax_ids': [Command.link(cls.tax_10.id)],
        })
        cls.tax_other.fiscal_position_ids = [Command.link(cls.fpos_other.id)]

        cls.customer.property_account_position_id = cls.fpos
        cls.other_customer.property_account_position_id = cls.fpos_other

        cls.product_10 = cls.create_product('Product 10', cls.categ_basic, 100, tax_ids=cls.tax_10.ids)
        cls.product_15 = cls.create_product('Product 15', cls.categ_basic, 100, tax_ids=cls.tax_15.ids)

    def _sync_order(self, product, customer=False, taxes=None, draft=False):
        """ Create an order from the ui data, with the fiscal position of the
        customer. Like the frontend, the line holds the original taxes (the
        product ones, or `taxes`), not the mapped ones. """
        order_data = self.create_ui_order_data([(product, 1)], customer=customer)
        # `create_ui_order_data` sets tax_ids from the FP map, unlike orders created from the frontend
        order_data['lines'][0][2]['tax_ids'] = [Command.set((product.taxes_id if taxes is None else taxes).ids)]
        if draft:
            order_data['state'] = 'draft'
        res = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(res['pos.order'][0]['id'])

    def _reset_tax_ids_after_fiscal_position(self, lines):
        self.env.flush_all()
        self.env.cr.execute(
            "DELETE FROM pos_order_line_account_tax_fpos_rel WHERE pos_order_line_id IN %s",
            [tuple(lines.ids)],
        )
        self.env.invalidate_all()

    def test_tax_ids_after_fiscal_position_frozen(self):
        """ Changing the tax mapping of a fiscal position must not alter the
        taxes of existing orders. """
        self.open_new_session()
        order = self._sync_order(self.product_10, customer=self.customer)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.lines.tax_ids, self.tax_10)
        self.assertEqual(order.lines.tax_ids_after_fiscal_position, self.tax_20)

        # FP now maps 10% -> 25%
        self.tax_20.write({'fiscal_position_ids': [Command.clear()], 'original_tax_ids': [Command.clear()]})
        self.tax_25.write({
            'fiscal_position_ids': [Command.link(self.fpos.id)],
            'original_tax_ids': [Command.link(self.tax_10.id)],
        })
        self.env.invalidate_all()
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.lines.tax_ids, self.tax_10)
        self.assertEqual(order.lines.tax_ids_after_fiscal_position, self.tax_20)

        # changing the fiscal position of a processed order does not recompute
        order.fiscal_position_id = self.fpos_other
        self.assertEqual(order.lines.tax_ids_after_fiscal_position, self.tax_20)
        order.fiscal_position_id = False
        self.assertEqual(order.lines.tax_ids_after_fiscal_position, self.tax_20)

        # a change of the fiscal position of a draft order recomputes
        draft_order = self._sync_order(self.product_10, customer=self.customer, draft=True)
        self.assertEqual(draft_order.state, 'draft')
        self.assertEqual(draft_order.lines.tax_ids_after_fiscal_position, self.tax_25)
        draft_order.fiscal_position_id = False
        self.assertEqual(draft_order.lines.tax_ids_after_fiscal_position, self.tax_10)

    def test_init_storage_matches_map_tax(self):
        """ The initialization of the column must give the same result as
        `account.fiscal.position.map_tax`. """
        self.open_new_session()
        # FP also maps 15% -> 20% + 25%
        self.tax_25.write({
            'fiscal_position_ids': [Command.link(self.fpos.id)],
            'original_tax_ids': [Command.link(self.tax_15.id)],
        })
        self.tax_20.original_tax_ids = [Command.link(self.tax_15.id)]
        orders = self.env['pos.order']
        for customer, taxes in (
            (False, self.tax_10),                               # no fiscal position
            (self.customer, self.tax_10 | self.tax_15),         # mapped, 1 -> n
            (self.customer, self.tax_other | self.tax_10),      # other is removed
            (self.other_customer, self.tax_other),              # restricted to its own fp
            (self.customer, self.tax_25),                       # unmapped, restricted to fp
            (self.other_customer, self.tax_10),                 # no mapping: kept
            (self.customer, self.env['account.tax']),           # no tax
        ):
            orders |= self._sync_order(self.product_10, customer=customer, taxes=taxes, draft=True)
        lines = orders.lines
        expected = {line.id: line.order_id.fiscal_position_id.map_tax(line.tax_ids) for line in lines}
        self.assertEqual(expected[lines[1].id], self.tax_20 | self.tax_25)
        self.assertEqual(expected[lines[2].id], self.tax_20)

        self._reset_tax_ids_after_fiscal_position(lines)
        self.assertFalse(lines.tax_ids_after_fiscal_position)

        self.env['pos.order.line']._init_column_tax_ids_after_fiscal_position()
        self.env.invalidate_all()
        for line in lines:
            self.assertEqual(line.tax_ids_after_fiscal_position, expected[line.id], line.order_id.fiscal_position_id.name)

    def test_init_storage_keeps_archived_taxes(self):
        """ Archived taxes are kept by the initialization: old lines keep the
        taxes they were sold with. """
        self.open_new_session()
        order_no_fp = self._sync_order(self.product_15)
        order_fp = self._sync_order(self.product_10, customer=self.customer)
        self.pos_session.close_session_from_ui()
        (self.tax_15 | self.tax_20).active = False

        lines = (order_no_fp | order_fp).lines
        self._reset_tax_ids_after_fiscal_position(lines)
        self.env['pos.order.line']._init_column_tax_ids_after_fiscal_position()
        self.env.invalidate_all()
        lines = lines.with_context(active_test=False)
        self.assertEqual(lines[0].tax_ids_after_fiscal_position, self.tax_15)
        self.assertEqual(lines[1].tax_ids_after_fiscal_position, self.tax_20)
