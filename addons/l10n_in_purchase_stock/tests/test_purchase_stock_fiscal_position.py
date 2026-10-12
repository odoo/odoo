from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestPurchaseStockFiscalPosition(L10nInTestInvoicingCommon):

    def _create_confirmed_purchase(self, fiscal_position=False):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'fiscal_position_id': fiscal_position.id if fiscal_position else False,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_qty': 5.0,
                'price_unit': 100.0,
            })],
        })
        purchase_order.button_confirm()
        return purchase_order

    def test_get_fiscal_position_from_purchase_order(self):
        """ The receipt must expose the fiscal position of its purchase order,
        so that the e-waybill can fall back on it. """
        purchase_order = self._create_confirmed_purchase(fiscal_position=self.fp_in_inter_state)
        picking = purchase_order.picking_ids[0]
        self.assertEqual(
            picking._l10n_in_get_fiscal_position(),
            self.fp_in_inter_state,
        )

    def test_get_fiscal_position_without_purchase_order(self):
        """ Without a purchase order, the hook falls back on the base
        implementation (no fiscal position). """
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).in_type_id.id,
        })
        self.assertFalse(picking._l10n_in_get_fiscal_position())
