# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSubcontractingDropshippingValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        categ_form = Form(cls.env['product.category'])
        categ_form.name = 'fifo auto'
        categ_form.parent_id = cls.env.ref('product.product_category_all')
        categ_form.property_cost_method = 'fifo'
        categ_form.property_valuation = 'real_time'
        cls.categ_fifo_auto = categ_form.save()

        (cls.product_a | cls.product_b).type = 'product'

        cls.bom_a = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_a.product_tmpl_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, cls.partner_a.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_b.id, 'product_qty': 1.0}),
            ],
        })
        cls.dropship_picking_type = cls.env['stock.picking.type'].search([
            ('company_id', '=', cls.env.company.id),
            ('default_location_src_id.usage', '=', 'supplier'),
            ('default_location_dest_id.usage', '=', 'customer'),
        ], limit=1, order='sequence')

        cls.sbc_location = cls.env.company.subcontracting_location_id

        warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = warehouse.lot_stock_id
        cls.stock_location.return_location = True

        grp_multi_loc = cls.env.ref('stock.group_stock_multi_locations')
        cls.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})

        (cls.product_a | cls.product_b).categ_id = cls.categ_fifo_auto

    def create_po_validate_picking(self, quantity, price_unit):
        po = self.env['purchase.order'].create({
            "partner_id": self.partner_a.id,
            "picking_type_id": self.dropship_picking_type.id,
            "dest_address_id": self.partner_b.id,
            "order_line": [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_qty': quantity,
                'price_unit': price_unit,
                'taxes_id': False,
            })],
        })
        po.button_confirm()

        delivery = po.picking_ids
        res = delivery.button_validate()
        Form(self.env['stock.immediate.transfer'].with_context(res['context'])).save().process()
        return delivery

    def return_picking(self, picking, quantity, location):
        # return to subcontracting location
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking'))
        return_form.location_id = location
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = quantity
        return_wizard = return_form.save()
        return_id, _ = return_wizard._create_returns()
        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_lines.quantity_done = quantity
        return_picking.button_validate()
        return return_picking

    def test_valuation_subcontracted_and_dropshipped(self):
        """
        Product:
            - FIFO + Auto
            - Subcontracted
        Purchase 2 from Subcontractor to a customer (dropship).
        Then return 1 to subcontractor and one to stock
        It should generate the correct valuations AMLs
        """
        # pylint: disable=bad-whitespace
        all_amls_ids = self.env['account.move.line'].search_read([], ['id'])

        self.product_b.standard_price = 10

        delivery = self.create_po_validate_picking(2, 100)

        stock_in_acc_id = self.categ_fifo_auto.property_stock_account_input_categ_id.id
        stock_out_acc_id = self.categ_fifo_auto.property_stock_account_output_categ_id.id
        stock_valu_acc_id = self.categ_fifo_auto.property_stock_valuation_account_id.id

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            # Compensation of dropshipping value
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 20.0,  'credit': 0.0},
            # Receipt from subcontractor
            {'account_id': stock_in_acc_id,     'product_id': self.product_a.id,    'debit': 0.0,   'credit': 220.0},
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 220.0, 'credit': 0.0},
            # Delivery to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.product_b.id,    'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_out_acc_id,    'product_id': self.product_b.id,    'debit': 20.0,  'credit': 0.0},
            # Initial dropshipped value
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 0.0,   'credit': 200.0},
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 200.0, 'credit': 0.0},
        ])

        # return to subcontracting location
        self.return_picking(delivery, 1, self.sbc_location)

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 0.0,   'credit': 110.0},
            {'account_id': stock_in_acc_id,     'product_id': self.product_a.id,    'debit': 110.0, 'credit': 0.0},
        ])

        # return to stock location
        self.return_picking(delivery, 1, self.stock_location)

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 0.0,   'credit': 110.0},
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 110.0, 'credit': 0.0},
        ])

    def test_remaining_data_subcontracted_dropshipped_1(self):
        # Basic test: Do a Subcontract Dropship, and ensure that both moves
        #   Manufacturing->Subcontracting and Subcontracting->Customer creates valuation layers that cancels each
        #   others in value, quantity, remaining_value and remaining_qty
        delivery = self.create_po_validate_picking(2, 10)
        mo_layer = delivery.move_lines.move_orig_ids.stock_valuation_layer_ids
        sub_layers = delivery.move_lines.stock_valuation_layer_ids

        self.assertEqual(mo_layer.remaining_qty, 0)
        self.assertEqual(sub_layers.filtered(lambda svl: svl.quantity != 0).remaining_qty, 0)
        self.assertEqual(sum((mo_layer | sub_layers).mapped("remaining_qty")), 0)

        self.assertEqual(sum((mo_layer | sub_layers).mapped("value")), 0)
        self.assertEqual(sum((mo_layer | sub_layers).mapped("remaining_value")), 0)

    def test_remaining_data_subcontracted_dropshipped_2(self):
        # Do a Subcontract Dropship while the finished product has a negative global quantity,
        #   then, ensure that both moves Manufacturing->Subcontracting and Subcontracting->Customer
        #   creates valuation layers that cancels each others in value, quantity, remaining_value and remaining_qty
        self.env['stock.quant'].create({
            "location_id": self.stock_location.id,
            "product_id": self.product_a.id,
            "inventory_quantity": -10,
        }).action_apply_inventory()

        delivery = self.create_po_validate_picking(2, 10)
        mo_layer = delivery.move_lines.move_orig_ids.stock_valuation_layer_ids
        sub_layers = delivery.move_lines.stock_valuation_layer_ids

        self.assertEqual(mo_layer.remaining_qty, 0)
        self.assertEqual(sub_layers.filtered(lambda svl: svl.quantity != 0).remaining_qty, 0)
        self.assertEqual(sum((mo_layer | sub_layers).mapped("remaining_qty")), 0)

        self.assertEqual(sum((mo_layer | sub_layers).mapped("value")), 0)
        self.assertEqual(sum((mo_layer | sub_layers).mapped("remaining_value")), 0)

        all_layers = self.product_a.stock_valuation_layer_ids
        self.assertEqual(sum(all_layers.mapped("quantity")), sum(all_layers.mapped("remaining_qty")))

    def test_remaining_data_subcontracted_dropshipped_3(self):
        # Test the remaining_qty for Subcontract Dropship Return to the stock or subcontraction location
        delivery = self.create_po_validate_picking(2, 10)

        # Return the product to stock location,
        # this is similar to an IN move and should be treated as such for the remaining data
        return_pck = self.return_picking(delivery, 1, self.stock_location)
        ret_layer = return_pck.move_lines.stock_valuation_layer_ids.ensure_one()
        self.assertEqual(ret_layer.remaining_qty, 1)

        # Return the product to subcontracting location, because the subcontracting location is valued,
        # this is similar to an IN move and should be treated as such for the remaining data
        return_pck = self.return_picking(delivery, 1, self.sbc_location)
        ret_layer = return_pck.move_lines.stock_valuation_layer_ids.ensure_one()
        self.assertEqual(ret_layer.remaining_qty, 1)

    def test_remaining_data_subcontracted_dropshipped_4(self):
        # Ensure that in a Subcontract Dropship, the move Subcontracting->Customer takes the remaining_qty
        #   of the move Production->Subcontracting.
        self.env['stock.quant'].create({
            "location_id": self.stock_location.id,
            "product_id": self.product_a.id,
            "inventory_quantity": 2,
        }).action_apply_inventory()
        adj_layer = self.product_a.stock_valuation_layer_ids.ensure_one()
        self.assertEqual(adj_layer.remaining_qty, 2)

        delivery = self.create_po_validate_picking(2, 10)
        mo_layer = delivery.move_lines.move_orig_ids.stock_valuation_layer_ids
        sub_layers = delivery.move_lines.stock_valuation_layer_ids

        self.assertEqual(adj_layer.remaining_qty, 2)
        self.assertEqual(mo_layer.remaining_qty, 0)
        self.assertEqual(sub_layers.filtered(lambda svl: svl.quantity != 0).remaining_qty, 0)
