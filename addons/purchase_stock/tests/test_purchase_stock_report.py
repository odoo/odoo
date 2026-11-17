# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import Form
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestPurchaseStockReports(TestReportsCommon):
    def _create_po(self, qty, *, product=None, uom=None, partner=None):
        product = product or self.product
        po = self.env['purchase.order'].create({
            'partner_id': (partner or self.partner).id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': qty,
                'product_uom': (uom or product.uom_id).id,
            })],
        })
        po.button_confirm()
        return po

    def _return_picking(self, picking, qty, location=None):
        wizard = Form(self.env['stock.return.picking'].with_context(
            active_ids=picking.ids,
            active_id=picking.id,
            active_model='stock.picking',
        )).save()
        wizard.product_return_moves.quantity = qty
        return_picking = self.env['stock.picking'].browse(wizard.action_create_returns()['res_id'])
        if location:
            return_picking.location_dest_id = location
        return_picking.button_validate()

    def test_report_forecast_1_purchase_order_multi_receipt(self):
        """ Create a PO for 5 product, receive them then increase the quantity to 10.
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 5
        po = po_form.save()

        # Checks the report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0, "Must have 0 line for now.")
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 5)
        self.assertEqual(pending_qty_in, 5)

        # Confirms the PO and checks the report again.
        po.button_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in']['id'], po.id)
        self.assertEqual(lines[0]['quantity'], 5)
        self.assertEqual(lines[0]['document_out'], False)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

        # Receives 5 products.
        receipt = po.picking_ids
        receipt.button_validate()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

        # Increase the PO quantity to 10, so must create a second receipt.
        po_form = Form(po)
        with po_form.order_line.edit(0) as line:
            line.product_qty = 10
        po = po_form.save()
        # Checks the report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1, "Must have 1 line for now.")
        self.assertEqual(lines[0]['document_in']['id'], po.id)
        self.assertEqual(lines[0]['quantity'], 5)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

    def test_report_forecast_2_purchase_order_three_step_receipt(self):
        """ Create a PO for 4 product, receive them then increase the quantity
        to 10, but use three steps receipt.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        # Configure warehouse.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.reception_steps = 'three_steps'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 4
        po = po_form.save()

        # Checks the report -> Must be empty for now, just display some pending qty.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0, "Must have 0 line for now.")
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 4)
        self.assertEqual(pending_qty_in, 4)

        # Confirms the PO and checks the report again.
        po.button_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in']['id'], po.id)
        self.assertEqual(lines[0]['quantity'], 4)
        self.assertEqual(lines[0]['document_out'], False)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)
        # Get back the different transfers.
        receipt = po.picking_ids

        # Receives 4 products.
        receipt.button_validate()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

        # Increase the PO quantity to 10, so must create a second receipt.
        po_form = Form(po)
        with po_form.order_line.edit(0) as line:
            line.product_qty = 10
        po = po_form.save()
        # Checks the report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in']['id'], po.id)
        self.assertEqual(lines[0]['quantity'], 6)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

    def test_report_forecast_3_report_line_corresponding_to_po_line_highlighted(self):
        """ When accessing the report from a PO line, checks if the correct PO line is highlighted in the report
        """
        # We create 2 identical PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 5
        po1 = po_form.save()
        po1.button_confirm()
        po2 = po1.copy()
        po2.button_confirm()

        # Check for both PO if the highlight (is_matched) corresponds to the correct PO
        for po in [po1, po2]:
            context = po.order_line[0].action_product_forecast_report()['context']
            _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids, context=context)
            for line in lines:
                if line['document_in']['id'] == po.id:
                    self.assertTrue(line['is_matched'], "The corresponding PO line should be matched in the forecast report.")
                else:
                    self.assertFalse(line['is_matched'], "A line of the forecast report not linked to the PO shoud not be matched.")

    def test_approval_and_forecasted_qty(self):
        """
        When a PO is waiting for an approval, its quantities should be included
        in the draft quantity count
        """
        self.env.company.po_double_validation = 'two_step'
        self.env.company.po_double_validation_amount = 0

        basic_purchase_user = mail_new_test_user(
            self.env,
            login='basic_purchase_user',
            groups='base.group_user,purchase.group_purchase_user',
        )

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 50
        po_form.save()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 100
        po = po_form.save()
        po.with_user(basic_purchase_user).button_confirm()

        docs = self.get_report_forecast(product_template_ids=self.product_template.ids)[1]
        self.assertEqual(docs['draft_purchase_qty'], 150)

    def test_purchase_report_effective_days_to_arrival(self):
        """ Test that 'Effective Days To Arrival' counts the days between the
        order confirmation date and the effective receipt date.
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'date_order': datetime.now() - timedelta(days=10),
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_qty': 1,
                'date_planned': datetime.now() + timedelta(days=5),
            })],
        })
        po.button_confirm()
        po.picking_ids.button_validate()

        po.flush_model()
        po.picking_ids.flush_recordset(['date_done'])
        report = self.env['purchase.report'].read_group(
            [('order_id', '=', po.id)],
            ['order_id', 'days_to_arrival'],
            ['order_id'],
        )
        self.assertEqual(round(report[0]['days_to_arrival']), 10)

    def test_vendor_delay_report_with_uom(self):
        """
        PO 12 units x P
        Receive 1 dozen x P
        -> 100% received
        """
        uom_12 = self.env.ref('uom.product_uom_dozen')

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 12
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt_move = receipt.move_ids
        receipt_move.move_line_ids.unlink()
        receipt_move.move_line_ids = [(0, 0, {
            'location_id': receipt_move.location_id.id,
            'location_dest_id': receipt_move.location_dest_id.id,
            'product_id': self.product.id,
            'product_uom_id': uom_12.id,
            'quantity': 1,
            'picking_id': receipt.id,
        })]
        receipt.move_ids.picked = True
        receipt.button_validate()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 12)
        self.assertEqual(data['qty_total'], 12)
        self.assertEqual(data['on_time_rate'], 100)
        self.assertEqual(self.partner.on_time_rate, 100)

    def test_vendor_delay_report_with_multi_location(self):
        """
        PO 10 units x P
        Receive
            - 6 x P in Child Location 01
            - 4 x P in Child Location 02
        -> 100% received
        """
        if not self.stock_location.child_ids:
            self.env['stock.location'].create([{
                'name': 'Shelf 1',
                'location_id': self.stock_location.id,
            }, {
                'name': 'Shelf 2',
                'location_id': self.stock_location.id,
            }])

        child_loc_01, child_loc_02 = self.stock_location.child_ids

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt_move = receipt.move_ids
        receipt_move.move_line_ids.unlink()
        receipt_move.move_line_ids = [(0, 0, {
            'location_id': receipt_move.location_id.id,
            'location_dest_id': child_loc_01.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'quantity': 6,
            'picking_id': receipt.id,
        }), (0, 0, {
            'location_id': receipt_move.location_id.id,
            'location_dest_id': child_loc_02.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'quantity': 4,
            'picking_id': receipt.id,
        })]
        receipt.move_ids.picked = True
        receipt.button_validate()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 10)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 100)
        self.assertEqual(self.partner.on_time_rate, 100)

    def test_vendor_delay_report_with_backorder(self):
        """
        PO 10 units x P
        Receive 6 x P with backorder
        -> 60% received
        Process the backorder
        -> 100% received
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01_move = receipt01.move_ids
        receipt01_move.quantity = 6
        Form.from_action(self.env, receipt01.button_validate()).save().process()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 6)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 60)
        self.assertEqual(self.partner.on_time_rate, 60)

        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.quantity = 4
        receipt02.move_ids.picked = True
        receipt02.button_validate()

        (receipt01 | receipt02).move_ids.invalidate_recordset()
        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 10)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 100)
        self.partner.invalidate_recordset(fnames=['on_time_rate'])
        self.assertEqual(self.partner.on_time_rate, 100)

    def test_vendor_delay_report_without_backorder(self):
        """
        PO 10 units x P
        Receive 6 x P without backorder
        -> 60% received
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01_move = receipt01.move_ids
        receipt01_move.quantity = 6
        receipt01_move.picked = True
        Form.from_action(self.env, receipt01.button_validate()).save().process_cancel_backorder()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 6)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 60)
        self.assertEqual(self.partner.on_time_rate, 60)

    def test_vendor_delay_report_with_duplicate_receipt_without_backorder(self):
        """
        PO 10 units x P
        Receive 6 x P without backorder
        Duplicate picking with remaining 4 x P
        -> 100% received
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 6
        action = receipt01.button_validate()
        Form(self.env[action['res_model']].with_context(action['context'])).save().process_cancel_backorder()
        receipt02 = receipt01.copy()
        receipt02.move_ids.write({
            'product_uom_qty': 4,
        })
        receipt02.button_validate()
        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['qty_on_time'], 10)
        self.assertEqual(data['on_time_rate'], 100)
        self.assertEqual(self.partner.on_time_rate, 100)

    def test_vendor_delay_report_capped_returns(self):
        """The on-time rate mustn't exceed 100% per line. It must ignore returns (wherever they go)
        and only count the lines of confirmed POs that were (partly) received. The rates on the
        vendor and in the report must always agree."""

        uom_dozen = self.env.ref('uom.product_uom_dozen')
        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', '1')

        # A regular delivery. 100% expected.
        receipt = self._create_po(1, uom=uom_dozen).picking_ids
        self.assertEqual(receipt.move_ids.product_uom, uom_dozen)
        receipt.button_validate()
        self.assertAlmostEqual(self.partner.on_time_rate, 100, places=2,
            msg="1 dozen received for 1 dozen ordered: 12 of 12 on time.")

        # An overdelivery. The excess dozen is ignored.
        receipt = self._create_po(1, uom=uom_dozen).picking_ids
        receipt.move_ids.quantity = 2
        receipt.button_validate()
        self.assertAlmostEqual(self.partner.on_time_rate, 100, places=2,
            msg="2 dozens received for 1 dozen ordered: 24 of 24 on time.")

        # An overdelivery in the product UoM. It must correctly add up dozens with units.
        receipt = self._create_po(10).picking_ids
        receipt.move_ids.quantity = 15
        receipt.button_validate()
        self.assertAlmostEqual(self.partner.on_time_rate, 100, places=2,
            msg="15 received for 10 ordered: 34 of 34 on time.")

        # An overdelivery through a backorder. We still expect to receive the original quantity.
        receipt = self._create_po(10).picking_ids
        receipt.move_ids.quantity = 6
        Form.from_action(self.env, receipt.button_validate()).save().process()
        receipt.backorder_ids.move_ids.quantity = 8
        receipt.backorder_ids.button_validate()
        self.assertAlmostEqual(self.partner.on_time_rate, 100, places=2,
            msg="6 + 8 (backorder) received for 10 ordered: 44 of 44 on time.")

        report_rate = self.env['vendor.delay.report']._read_group(
            [('partner_id', '=', self.partner.id)], [], ['on_time_rate:sum'])
        self.assertAlmostEqual(report_rate[0][0], 100, places=2, msg="44/44 on-time rate")

        po = self._create_po(10)
        po.picking_ids.button_validate()
        # Unreceived and underdue means it doesn't count as late yet.
        unreceived_po = po.copy()
        unreceived_po.button_confirm()
        # Cancelled means it doesn't count as late either.
        cancelled_po = po.copy()
        cancelled_po.button_confirm()
        cancelled_po.button_cancel()
        self.assertAlmostEqual(self.partner.on_time_rate, 100, places=2,
            msg="10 unreceived and 10 cancelled for 10 ordered: 54 of 54 on time.")

        # Combo and service products are ignored.
        service_product, combo_product = self.env['product.product'].create([{
            'name': "Assembly",
            'type': 'service',
        }, {
            'name': "Promo Combo",
            'type': 'combo',
            'combo_ids': [Command.create({
                'name': "Combo Choice",
                'combo_item_ids': [Command.create({'product_id': self.product.id})],
            })],
        }])
        internal_location = self.env['stock.location'].create({
            'name': "Reject Bin",
            'usage': 'internal',
            'location_id': self.stock_location.location_id.id,
        })
        po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({'product_id': self.product.id, 'product_qty': 10}),
                Command.create({'product_id': self.product1.id, 'product_qty': 2}),
                Command.create({'product_id': self.serial_product.id, 'product_qty': -2}),
                Command.create({'product_id': service_product.id, 'product_qty': 3}),
                Command.create({'product_id': combo_product.id, 'product_qty': 4}),
            ],
        })
        po.button_confirm()
        # Partial reception means part of the delivery wasn't received on time.
        receipt = po.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
        receipt.move_ids.filtered(lambda m: m.product_id == self.product).quantity = 8
        receipt.move_ids.filtered(lambda m: m.product_id == self.product1).quantity = 0
        Form.from_action(self.env, receipt.button_validate()).save().process_cancel_backorder()
        # Returns and internal transfers are ignored.
        self._return_picking(receipt, 2)
        self._return_picking(receipt, 2, internal_location)
        self.assertAlmostEqual(self.partner.on_time_rate, 62 / 66 * 100, places=2,
            msg="8 of 10 received without backorder, 2 returned to the vendor, "
                "2 went to an internal location, and 0 of 2 received: 62 of 66 on time.")

        report_rate = self.env['vendor.delay.report']._read_group(
            [('partner_id', '=', self.partner.id)], [], ['on_time_rate:sum'])
        self.assertAlmostEqual(report_rate[0][0], 62 / 66 * 100, places=2, msg="62/66 on-time rate")

        # Partial delivery in different UoM.
        uom_unit = self.env.ref('uom.product_uom_unit')
        other_partner = self.env['res.partner'].create({'name': "Ersatz Co"})
        uom_triple = self.env['uom.uom'].create({
            'name': "Three-pack",
            'category_id': uom_unit.category_id.id,
            'uom_type': 'bigger',
            'factor_inv': 3,
            'rounding': 0.01,
        })
        product_triple = self.env['product.product'].create({
            'name': "Three-piece set",
            'is_storable': True,
            'uom_id': uom_triple.id,
            'uom_po_id': uom_triple.id,
        })
        po = self._create_po(2, product=product_triple, uom=uom_unit, partner=other_partner)
        receipt = po.picking_ids
        receipt.move_ids.quantity = 1
        Form.from_action(self.env, receipt.button_validate()).save().process_cancel_backorder()
        self.assertAlmostEqual(other_partner.on_time_rate, 50, places=2,
            msg="1 received for 2 ordered: 1 of 2 on time.")

        report_rate = self.env['vendor.delay.report']._read_group(
            [('partner_id', '=', other_partner.id)], [], ['on_time_rate:sum'])
        self.assertAlmostEqual(report_rate[0][0], 50, places=2, msg="1/2 on-time rate")

        # Exact delivery in a finer UoM. 2 units stored as 0,67 six-packs received as 0,6667 six-packs.
        # If the UoM calculations are correct, it should add up to 100%.
        uom_partner = self.env['res.partner'].create({'name': "Exact Inc"})
        po = self._create_po(2, product=product_triple, uom=uom_unit, partner=uom_partner)
        po.picking_ids.button_validate()
        self.assertAlmostEqual(uom_partner.on_time_rate, 100, places=2,
            msg="2 received for 2 ordered: 2 of 2 on time.")

        report_rate = self.env['vendor.delay.report']._read_group(
            [('partner_id', '=', uom_partner.id)], [], ['on_time_rate:sum'])
        self.assertAlmostEqual(report_rate[0][0], 100, places=2, msg="2/2 on-time rate")

        # Partial delivery over several moves of one line.
        backorder_partner = self.env['res.partner'].create({'name': "Bake Order"})
        receipt = self._create_po(10, partner=backorder_partner).picking_ids
        receipt.move_ids.quantity = 3
        Form.from_action(self.env, receipt.button_validate()).save().process()
        backorder = receipt.backorder_ids
        backorder.move_ids.quantity = 3
        Form.from_action(self.env, backorder.button_validate()).save().process_cancel_backorder()
        self.assertAlmostEqual(backorder_partner.on_time_rate, 60, places=2,
            msg="3 + 3 (backorder) received for 10 ordered: 6 of 10 on time.")

        report_rate = self.env['vendor.delay.report']._read_group(
            [('partner_id', '=', backorder_partner.id)], [], ['on_time_rate:sum'])
        self.assertAlmostEqual(report_rate[0][0], 60, places=2, msg="6/10 on-time rate")
