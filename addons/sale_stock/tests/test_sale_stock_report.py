# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo.tools import html2plaintext

from odoo import Command
from odoo.tests import Form, tagged
from odoo.exceptions import AccessError
from odoo.addons.stock.tests.test_report import TestReportsCommon
from odoo.addons.sale.tests.common import TestSaleCommon


class TestSaleStockReports(TestReportsCommon):
    def test_report_forecast_1_sale_order_replenishment(self):
        """ Create and confirm two sale orders: one for the next week and one
        for tomorrow. Then check in the report it's the most urgent who is
        linked to the qty. on stock.
        """
        # make sure first picking doesn't auto-assign
        self.picking_type_out.reservation_method = 'manual'

        today = datetime.today()
        # Put some quantity in stock.
        quant_vals = {
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'quantity': 5,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(quant_vals)
        # Create a first SO for the next week.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        # so_form.validity_date = today + timedelta(days=7)
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so_1 = so_form.save()
        so_1.action_confirm()
        so_1.picking_ids.scheduled_date = today + timedelta(days=7)

        # Create a second SO for tomorrow.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        # so_form.validity_date = today + timedelta(days=1)
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so_2 = so_form.save()
        so_2.action_confirm()
        so_2.picking_ids.scheduled_date = today + timedelta(days=1)

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 2)
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1['quantity'], 5)
        self.assertTrue(line_1['replenishment_filled'])
        self.assertEqual(line_1['document_out']['id'], so_2.id)
        self.assertEqual(line_2['quantity'], 5)
        self.assertEqual(line_2['replenishment_filled'], False)
        self.assertEqual(line_2['document_out']['id'], so_1.id)

    def test_report_forecast_2_report_line_corresponding_to_so_line_highlighted(self):
        """ When accessing the report from a SO line, checks if the correct SO line is highlighted in the report
        """
        # We create 2 identical SO
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        with so_form.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 5
        so1 = so_form.save()
        so1.action_confirm()
        so2 = so1.copy()
        so2.action_confirm()

        # Check for both SO if the highlight (is_matched) corresponds to the correct SO
        for so in [so1, so2]:
            context = {"move_to_match_ids": so.order_line.move_ids.ids}
            _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids, context=context)
            for line in lines:
                if line['document_out']['id'] == so.id:
                    self.assertTrue(line['is_matched'], "The corresponding SO line should be matched in the forecast report.")
                else:
                    self.assertFalse(line['is_matched'], "A line of the forecast report not linked to the SO shoud not be matched.")

    def test_report_forecast_3_unreserve_2_step_delivery(self):
        """
        Check that the forecast correctly reconciles the outgoing moves
        that are part of a chain with stock availability when unreserved.
        """
        warehouse = self.env.ref("stock.warehouse0")
        warehouse.delivery_steps = 'pick_ship'
        product = self.product
        # Put 5 units in stock
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 5)
        # Create and confirm an SO for 3 units
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 3,
                }),
            ],
        })
        so.action_confirm()
        _, _, lines = self.get_report_forecast(product_template_ids=product.product_tmpl_id.ids)
        outgoing_line = next(filter(lambda line: line.get('document_out'), lines))
        self.assertEqual(
            (outgoing_line['document_out']['id'], outgoing_line['quantity'], outgoing_line['replenishment_filled'], outgoing_line['reservation']['id']),
            (so.id, 3.0, True, so.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pick_type_id).id)
        )
        stock_line = next(filter(lambda line: not line.get('document_out'), lines))
        self.assertEqual(
            (stock_line['quantity'], stock_line['replenishment_filled'], stock_line['reservation']),
            (2.0, True, False)
        )
        # unrerseve the PICK delivery
        pick_delivery = so.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pick_type_id)
        pick_delivery.do_unreserve()
        _, _, lines = self.get_report_forecast(product_template_ids=product.product_tmpl_id.ids)
        outgoing_line = next(filter(lambda line: line.get('document_out'), lines))
        self.assertEqual(
            (outgoing_line['document_out']['id'], outgoing_line['quantity'], outgoing_line['replenishment_filled'], outgoing_line['reservation']),
            (so.id, 3.0, True, False)
        )
        stock_line = next(filter(lambda line: not line.get('document_out'), lines))
        self.assertEqual(
            (stock_line['quantity'], stock_line['replenishment_filled'], stock_line['reservation']),
            (2.0, True, False)
        )

    def test_report_forecast_4_so_from_another_salesman(self):
        """ Try accessing the forecast with a user that has only access to his SO while another user has created:
            - A draft Sale Order
            - A confirmed Sale Order
            The report shoud be usable by that user, and while he cannot open those SO, he should still see them to have the correct
            informations in the report.
        """
        # Create the SO & confirm it with first user
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.partner
            with so_form.order_line.new() as line:
                line.product_id = self.product
                line.product_uom_qty = 3
            sale_order = so_form.save()
        sale_order.action_confirm()

        # Create a draft SO with the same user for the same product
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.partner
            with so_form.order_line.new() as line:
                line.product_id = self.product
                line.product_uom_qty = 2
            draft = so_form.save()

        # Create second user which only has access to its own documents
        other = self.env['res.users'].create({
            'name': 'Other Salesman',
            'login': 'other',
            'group_ids': [
                Command.link(self.env.ref('sales_team.group_sale_salesman').id),
                Command.link(self.env.ref('stock.group_stock_user').id),
            ],
        })

        # Need to reset the cache otherwise it wouldn't trigger an Access Error anyway as the Sale Order is already there.
        sale_order.env.invalidate_all()
        report_values = self.env['stock.forecasted_product_product'].with_user(other).get_report_values(docids=self.product.ids)
        self.assertEqual(len(report_values['docs']['lines']), 1)
        self.assertEqual(report_values['docs']['lines'][0]['document_out']['name'], sale_order.name)
        self.assertEqual(len(report_values['docs']['product'][self.product.id]['draft_sale_orders']), 1)
        self.assertEqual(report_values['docs']['product'][self.product.id]['draft_sale_orders'][0]['name'], draft.name)

        # While 'other' can see these SO on the report, they shouldn't be able to access them.
        with self.assertRaises(AccessError):
            sale_order.with_user(other).check_access('read')
        with self.assertRaises(AccessError):
            draft.with_user(other).check_access('read')

    def test_add_reference_remove_reference_works_with_multiple_records(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5,
            })],
        })
        so.action_confirm()
        so_delivery = so.picking_ids

        so_delivery.reference_ids.copy()

        picking_receipt = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'partner_id': self.partner.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 18,
            })],
        })
        picking_receipt.action_confirm()

        self.env['report.stock.report_reception']._action_assign(
            picking_receipt.move_ids,
            so_delivery.move_ids,
        )
        self.assertEqual(picking_receipt.move_ids.reference_ids, so_delivery.move_ids.reference_ids)

        self.env['report.stock.report_reception']._action_unassign(
            picking_receipt.move_ids,
            so_delivery.move_ids,
        )
        self.assertNotIn(picking_receipt.move_ids.reference_ids, so_delivery.move_ids.reference_ids)


@tagged('post_install', '-at_install')
class TestSaleStockInvoices(TestSaleCommon):

    def setUp(self):
        super(TestSaleStockInvoices, self).setUp()
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('stock.group_production_lot').id)]})
        self.product_by_lot = self.env['product.product'].create({
            'name': 'Product By Lot',
            'is_storable': True,
            'tracking': 'lot',
        })
        self.product_by_usn = self.env['product.product'].create({
            'name': 'Product By USN',
            'is_storable': True,
            'tracking': 'serial',
        })
        self.warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.stock_location = self.warehouse.lot_stock_id
        lot = self.env['stock.lot'].create({
            'name': 'LOT0001',
            'product_id': self.product_by_lot.id,
        })
        self.usn01 = self.env['stock.lot'].create({
            'name': 'USN0001',
            'product_id': self.product_by_usn.id,
        })
        self.usn02 = self.env['stock.lot'].create({
            'name': 'USN0002',
            'product_id': self.product_by_usn.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 10, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(self.product_by_usn, self.stock_location, 1, lot_id=self.usn01)
        self.env['stock.quant']._update_available_quantity(self.product_by_usn, self.stock_location, 1, lot_id=self.usn02)

    def test_invoice_less_than_delivered(self):
        """
        Suppose the lots are printed on the invoices.
        A user invoice a tracked product with a smaller quantity than delivered.
        On the invoice, the quantity of the used lot should be the invoiced one.
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'group_ids': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_lot.name, 'product_id': self.product_by_lot.id, 'product_uom_qty': 5}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.write({'quantity': 5, 'picked': True})
        picking.button_validate()

        invoice = so._create_invoices()
        with Form(invoice) as form:
            with form.invoice_line_ids.edit(0) as line:
                line.quantity = 2
        invoice.action_post()

        html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n2.00Units\nLOT0001', "There should be a line that specifies 2 x LOT0001")

    def test_invoice_before_delivery(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells a tracked product, its invoicing policy is "Ordered quantities"
        A user invoice a tracked product with a smaller quantity than delivered.
        On the invoice, the quantity of the used lot should be the invoiced one.
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'group_ids': [(4, display_lots.id), (4, display_uom.id)]})

        self.product_by_lot.invoice_policy = "order"

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_lot.name, 'product_id': self.product_by_lot.id, 'product_uom_qty': 4}),
            ],
        })
        so.action_confirm()

        invoice = so._create_invoices()
        invoice.action_post()

        picking = so.picking_ids
        picking.move_ids.write({'quantity': 4, 'picked': True})
        picking.button_validate()

        html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n4.00Units\nLOT0001', "There should be a line that specifies 4 x LOT0001")

    def test_picking_description(self):
        """
        Verify that for a no-variant product, the product name is not included as the first element in the picking description,
        as this avoids repeating the name on the delivery slip.
        """

        product_attr = self.env['product.attribute'].create({'name': 'Color', 'create_variant': 'no_variant'})
        product_attrv1, product_attrv2 = self.env['product.attribute.value'].create([
            {'name': 'Value1', 'attribute_id': product_attr.id},
            {'name': 'Value2', 'attribute_id': product_attr.id},
        ])
        product_template_no_variant = self.env['product.template'].create({
            'name': 'product name',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attr.id,
                    'value_ids': [Command.set([product_attrv1.id, product_attrv2.id])],
                })]
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'name': product_template_no_variant.name,
                'product_id': product_template_no_variant.product_variant_id.id,
                'product_uom_qty': 4,
                'product_no_variant_attribute_value_ids': product_template_no_variant.product_variant_id.attribute_line_ids.product_template_value_ids
                }),
            ],
        })
        so.action_confirm()
        picking = so.picking_ids[0]
        picking_description = picking.move_ids._get_report_description_picking()
        self.assertEqual(picking_description, 'Color: Value1\nColor: Value2')

    def test_backorder_and_several_invoices(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells 2 tracked-by-usn products, he delivers 1 product and invoices it
        Then, he delivers the other one and invoices it too. Each invoice should have the
        correct USN
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'group_ids': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_usn.name, 'product_id': self.product_by_usn.id, 'product_uom_qty': 2}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.move_line_ids[0].quantity = 1
        picking.button_validate()

        invoice01 = so._create_invoices()
        with Form(invoice01) as form:
            with form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        invoice01.action_post()

        backorder = picking.backorder_ids
        backorder.move_ids.move_line_ids.quantity = 1
        backorder.button_validate()

        IrActionsReport = self.env['ir.actions.report']
        html = IrActionsReport._render_qweb_html('account.report_invoice_with_payments', invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should be a line that specifies 1 x USN0001")
        self.assertNotIn('USN0002', text)

        invoice02 = so._create_invoices()
        invoice02.action_post()
        html = IrActionsReport._render_qweb_html('account.report_invoice_with_payments', invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0002', "There should be a line that specifies 1 x USN0002")
        self.assertNotIn('USN0001', text)

        # Posting the second invoice shouldn't change the result of the first one
        html = IrActionsReport._render_qweb_html('account.report_invoice_with_payments', invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should still be a line that specifies 1 x USN0001")
        self.assertNotIn('USN0002', text)

        # Resetting and posting again the first invoice shouldn't change the results
        invoice01.button_draft()
        invoice01.action_post()
        html = IrActionsReport._render_qweb_html('account.report_invoice_with_payments', invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should still be a line that specifies 1 x USN0001")
        self.assertNotIn('USN0002', text)
        html = IrActionsReport._render_qweb_html('account.report_invoice_with_payments', invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0002', "There should be a line that specifies 1 x USN0002")
        self.assertNotIn('USN0001', text)

    def test_invoice_with_several_returns(self):
        """
        Mix of returns and partial invoice
        - Product P tracked by lot
        - SO with 10 x P
        - Deliver 10 x Lot01
        - Return 10 x Lot01
        - Deliver 03 x Lot02
        - Invoice 02 x P
        - Deliver 05 x Lot02 + 02 x Lot03
        - Invoice 08 x P
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'group_ids': [(4, display_lots.id), (4, display_uom.id)]})

        lot01 = self.env['stock.lot'].search([('name', '=', 'LOT0001')])
        lot02, lot03 = self.env['stock.lot'].create([{
            'name': name,
            'product_id': self.product_by_lot.id,
        } for name in ['LOT0002', 'LOT0003']])
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 8, lot_id=lot02)
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 2, lot_id=lot03)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_lot.name, 'product_id': self.product_by_lot.id, 'product_uom_qty': 10}),
            ],
        })
        so.action_confirm()

        # Deliver 10 x LOT0001
        delivery01 = so.picking_ids
        delivery01.move_ids.write({'quantity': 10, 'picked': True})
        delivery01.button_validate()
        self.assertEqual(delivery01.move_line_ids.lot_id.name, 'LOT0001')

        # Return delivery01 (-> 10 x LOT0001)
        return_form = Form(self.env['stock.return.picking'].with_context(active_ids=[delivery01.id], active_id=delivery01.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 10
        action = return_wizard.action_create_returns()
        pick_return = self.env['stock.picking'].browse(action['res_id'])

        move_form = Form(pick_return.move_ids, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as line:
            line.lot_id = lot01
            line.quantity = 10
        move_form.save()
        pick_return.move_ids.picked = True
        pick_return.button_validate()

        # Return pick_return
        return_form = Form(self.env['stock.return.picking'].with_context(active_ids=[pick_return.id], active_id=pick_return.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 10
        action = return_wizard.action_create_returns()
        delivery02 = self.env['stock.picking'].browse(action['res_id'])

        # Deliver 3 x LOT0002
        delivery02.do_unreserve()
        move_form = Form(delivery02.move_ids, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.new() as line:
            line.lot_id = lot02
            line.quantity = 3
        move_form.save()
        delivery02.move_ids.picked = True
        Form.from_action(self.env, delivery02.button_validate()).save().process()

        # Invoice 2 x P
        invoice01 = so._create_invoices()
        with Form(invoice01) as form:
            with form.invoice_line_ids.edit(0) as line:
                line.quantity = 2
        invoice01.action_post()

        html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments', invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n2.00Units\nLOT0002', "There should be a line that specifies 2 x LOT0002")
        self.assertNotIn('LOT0001', text)

        # Deliver 5 x LOT0002 + 2 x LOT0003
        delivery03 = delivery02.backorder_ids
        delivery03.do_unreserve()
        move_form = Form(delivery03.move_ids, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.new() as line:
            line.lot_id = lot02
            line.quantity = 5
        with move_form.move_line_ids.new() as line:
            line.lot_id = lot03
            line.quantity = 2
        move_form.save()
        delivery03.move_ids.picked = True
        delivery03.button_validate()

        # Invoice 8 x P
        invoice02 = so._create_invoices()
        invoice02.action_post()

        html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments', invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n6.00Units\nLOT0002', "There should be a line that specifies 6 x LOT0002")
        self.assertRegex(text, r'Product By Lot\n2.00Units\nLOT0003', "There should be a line that specifies 2 x LOT0003")
        self.assertNotIn('LOT0001', text)

    def test_refund_cancel_invoices(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells 2 tracked-by-usn products, he delivers 2 products and invoices them
        Then he adds credit notes and issues a full refund. Receive the products.
        The reversed invoice should also have correct USN
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'group_ids': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_usn.name, 'product_id': self.product_by_usn.id, 'product_uom_qty': 2}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.move_line_ids[0].quantity = 1
        picking.move_ids.move_line_ids[1].quantity = 1
        picking.move_ids.picked = True
        picking.button_validate()

        invoice01 = so._create_invoices()
        invoice01.action_post()

        html = self.env['ir.actions.report']._render_qweb_html('account.report_invoice_with_payments', invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should be a line that specifies 1 x USN0001")
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0002', "There should be a line that specifies 1 x USN0002")

        # Refund the invoice
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice01.ids).create({
            'journal_id': invoice01.journal_id.id,
        })
        res = refund_wizard.refund_moves()
        refund_invoice = self.env['account.move'].browse(res['res_id'])
        refund_invoice.action_post()

        # recieve the returned product
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(active_ids=picking.ids, active_id=picking.sorted().ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 2
        res = return_wiz.action_create_returns()
        pick_return = self.env['stock.picking'].browse(res['res_id'])

        move_form = Form(pick_return.move_ids, view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as line:
            line.lot_id = self.usn01
            line.quantity = 1
        with move_form.move_line_ids.edit(1) as line:
            line.lot_id = self.usn02
            line.quantity = 1
        move_form.save()
        pick_return.move_ids.picked = True
        pick_return.button_validate()

        # reversed invoice
        html = self.env['ir.actions.report']._render_qweb_html('account.report_invoice_with_payments', refund_invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should be a line that specifies 1 x USN0001")
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0002', "There should be a line that specifies 1 x USN0002")

    def test_refund_modify_invoices(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells 1 tracked-by-usn products, he delivers 1 and invoices it
        Then he adds credit notes and issues full refund and new draft invoice.
        The new draft invoice should have correct USN
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'group_ids': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_usn.name, 'product_id': self.product_by_usn.id, 'product_uom_qty': 1}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.move_line_ids[0].quantity = 1
        picking.move_ids.picked = True
        picking.button_validate()

        invoice01 = so._create_invoices()
        invoice01.action_post()

        html = self.env['ir.actions.report']._render_qweb_html('account.report_invoice_with_payments', invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should be a line that specifies 1 x USN0001")

        # Refund the invoice with full refund and new draft invoice
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice01.ids).create({
            'journal_id': invoice01.journal_id.id,
        })
        res = refund_wizard.modify_moves()
        invoice02 = self.env['account.move'].browse(res['res_id'])
        invoice02.action_post()

        # new draft invoice
        html = self.env['ir.actions.report']._render_qweb_html('account.report_invoice_with_payments', invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00Units\nUSN0001', "There should be a line that specifies 1 x USN0001")
