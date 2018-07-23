# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError
from odoo.tests import Form

class TestPickingOwner(TestStockCommon):

    def setUp(self):
        super(TestPickingOwner, self).setUp()
        self.picking_out = self.env.ref('stock.picking_type_out')
        self.stock_location = self.env.ref('stock.stock_location_stock')

    def create_picking(self, picking_type, location_dest):
        """ Create picking based on picking type """
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = self.env.ref('base.res_partner_3')
        picking_form.picking_type_id = picking_type
        with picking_form.move_lines.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 5.0
            move.location_id = self.stock_location
            move.location_dest_id = location_dest
        picking_form.owner_id = self.env.ref('base.res_partner_1')
        picking = picking_form.save()
        return picking

    def test_picking_owner_asign(self):
        # ------------------------------------------
        # Receive shipment with owner.
        # -----------------------------------------

        # Create Incoming shipment and confirm it.
        incoming_picking = self.create_picking(self.env.ref('stock.picking_type_in'), self.stock_location)
        incoming_picking.action_confirm()
        # Assign Owner to shipment.
        incoming_picking._assign_owner()
        # Transfer Incoming shipment.
        wizard = incoming_picking.button_validate()
        immediate_transfer = self.env[wizard['res_model']].browse(wizard['res_id'])
        immediate_transfer.process()

        # ------------------------------------------------
        # Deliver shipment with owner.
        # --------------------------------------

        # Create Outgoing shipment and confirm it.
        outgoing_picking = self.create_picking(self.picking_out, self.env.ref('stock.stock_location_suppliers'))
        outgoing_picking.action_confirm()
        # Assign owner on Outgoing shipment
        outgoing_picking.action_assign()
        # Outgoing shipment owner change
        outgoing_picking.write({'owner_id': self.env.ref('base.res_partner_2').id})
        # System should raise warning to user that he need to unresearve picking first
        # then they can change owner.
        with self.assertRaises(UserError):
            outgoing_picking.onchange_picking_owner()
        # Outgoing shipment unreserve product
        outgoing_picking.do_unreserve()
        # Reassign owner on Outgoing shipment
        outgoing_picking.write({'owner_id': self.env.ref('base.res_partner_1').id})
        outgoing_picking.action_assign()
        # check the owner stock move owner and Outgoing shipment
        self.assertEqual(outgoing_picking.mapped('move_lines').restrict_partner_id.id, outgoing_picking.owner_id.id, "same owner product can be sell.")
        # Transfer Outgoing shipment.
        wizard = outgoing_picking.button_validate()
        immediate_transfer = self.env[wizard['res_model']].browse(wizard['res_id'])
        immediate_transfer.process()
