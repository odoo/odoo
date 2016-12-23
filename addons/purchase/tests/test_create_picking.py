# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.product.tests import common


class TestCreatePicking(common.TestProductCommon):

    def setUp(self):
        super(TestCreatePicking, self).setUp()
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product_id_1 = self.env.ref('product.product_product_8')
        self.product_id_2 = self.env.ref('product.product_product_11')
        res_users_purchase_user = self.env.ref('purchase.group_purchase_user')

        Users = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        self.user_purchase_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'pur@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [res_users_purchase_user.id])]})

        self.po_vals = {
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_id_1.name,
                    'product_id': self.product_id_1.id,
                    'product_qty': 5.0,
                    'product_uom': self.product_id_1.uom_po_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }

    def test_00_create_picking(self):

        # Draft purchase order created
        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')

        # Purchase order confirm
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase')
        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created')
        self.assertEqual(len(self.po.order_line.move_ids), 1, 'One move should be created')

        # Change purchase order line product quantity
        self.po.order_line.write({'product_qty': 7.0})
        self.assertEqual(len(self.po.order_line.move_ids), 2, 'Two move should be created')

        # Validate first shipment
        self.picking = self.po.picking_ids[0]
        self.picking.force_assign()
        self.picking.pack_operation_product_ids.write({'qty_done': 7.0})
        self.picking.do_new_transfer()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [7.0], 'Purchase: all products should be received')

        # create new order line
        self.po.write({'order_line': [
            (0, 0, {
                'name': self.product_id_2.name,
                'product_id': self.product_id_2.id,
                'product_qty': 5.0,
                'product_uom': self.product_id_2.uom_po_id.id,
                'price_unit': 250.0,
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })]})
        self.assertEqual(self.po.picking_count, 2, 'New picking should be created')
        moves = self.po.order_line.mapped('move_ids').filtered(lambda x: x.state not in ('done', 'cancel'))
        self.assertEqual(len(moves), 1, 'One move should be created')

    def test_01_check_double_validation(self):

        # make double validation two step
        self.env.user.company_id.write({'po_double_validation': 'two_step','po_double_validation_amount':2000.00})

        # Draft purchase order created
        self.po = self.env['purchase.order'].sudo(self.user_purchase_user).create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')

        # Purchase order confirm
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'to approve', 'Purchase: PO state should be "to approve".')

        # PO approved by manager
        self.po.button_approve()
        self.assertEqual(self.po.state, 'purchase', 'PO state should be "Purchase".')
