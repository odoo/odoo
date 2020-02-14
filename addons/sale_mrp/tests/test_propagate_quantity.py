# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import Form
from odoo.addons.stock.tests.common2 import TestStockCommon


class TestMTOPropagation(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route_manu = cls.warehouse_1.manufacture_pull_id.route_id.id
        cls.route_mto = cls.warehouse_1.mto_pull_id.route_id.id

        cls.product_manu = cls.env['product.product'].create({
            'name': 'Bird',
            'type': 'product',
            'route_ids': [(6, 0, [cls.route_manu, cls.route_mto])],
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.component1 = cls.env['product.product'].create({
            'name': 'Wings',
            'type': 'product',
        })
        cls.component2 = cls.env['product.product'].create({
            'name': 'Camera',
            'type': 'product',
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_manu.product_tmpl_id.id,
            'product_uom_id': cls.product_manu.uom_id.id,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.component1.id,
                    'product_qty': 1,
                    'product_uom_id': cls.component1.uom_id.id,
                }), (0, 0, {
                    'product_id': cls.component2.id,
                    'product_qty': 1,
                    'product_uom_id': cls.component1.uom_id.id,
                })
            ]
        })

    def _create_sale_order(self, uom=False):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse_1.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_manu.name,
                    'product_id': self.product_manu.id,
                    'product_uom_qty': 5,
                    'product_uom': uom or self.uom_unit.id,
                })
            ]
        })
        order.action_confirm()
        return order

    def test_basic_propagate_uom(self):
        """ Create a sales order for manufactured/mto product.

        The product to manufacture is sell in another UoM than the quant's one
        Decreasing the quantity to sell should decrease the quantity to produce
        on the production order."""
        so = self._create_sale_order(self.uom_dozen.id)

        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])

        self.assertEqual(len(mo), 1)
        self.assertEqual(mo.product_qty, 60)
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 3})]})
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(mo.product_qty, 36)

    def test_basic_propagate_1(self):
        """ Create a sales order for manufactured/mto product.

        A production order is created
        Decreasing the quantity to sell should decrease the quantity to produce
        on the production order."""
        so = self._create_sale_order()

        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])

        self.assertEqual(len(mo), 1)
        self.assertEqual(mo.product_qty, 5)
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 3})]})
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(mo.product_qty, 3)

    def test_basic_propagate_2(self):
        """ Create a sales order for manufactured/mto product.

        A production order is created
        Increasing the quantity to sell should create another production with the
        delta quantity."""
        so = self._create_sale_order()

        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])

        self.assertEqual(len(mo), 1)
        self.assertEqual(mo.product_qty, 5)
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 8})]})
        self.assertEqual(mo.state, 'confirmed')
        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])

        self.assertEqual(len(mo), 2)
        self.assertEqual(sum(mo.mapped('product_qty')), 8)

    def test_basic_propagate_3(self):
        """ Create a sales order for manufactured/mto product.

        A production order is created. Produce de goods then close the production
        Decreasing the quantity to sell should lead to an exception on the ."""
        so = self._create_sale_order()

        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])

        # produce product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mo.button_mark_done()
        so_form = Form(so)
        with so_form.order_line.edit(0) as line:
            with self.assertLogs(level="WARNING") as log_catcher:
                line.product_uom_qty = 3

            self.assertEqual(len(log_catcher.output), 1, "Exactly one warning should be logged")
        so = so_form.save()

    def test_pbm_sam_decrease(self):
        """ Create a sales order for manufactured/mto product.

        The production is set to be made in multiple steps (PBM & SAM)

        A production order is created.
        Decreasing the quantity to sell should decrease it on all the pickings as
        well as on the production order."""
        self.warehouse_1.manufacture_steps = 'pbm_sam'
        so = self._create_sale_order()

        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])
        pbm_move = mo.move_raw_ids.move_orig_ids.filtered(lambda m: m.product_id == self.component1)
        sam_move = mo.move_finished_ids.move_dest_ids
        self.assertEqual(len(pbm_move), 1)
        self.assertEqual(len(sam_move), 1)

        so_form = Form(so)
        with so_form.order_line.edit(0) as line:
            line.product_uom_qty = 3
        so = so_form.save()

        self.assertEqual(pbm_move.product_uom_qty, 3)
        self.assertEqual(sam_move.product_uom_qty, 3)
        self.assertEqual(mo.move_raw_ids.filtered(lambda m: m.product_id == self.component1).product_uom_qty, 3)

    def test_pbm_sam_increase(self):
        """ Create a sales order for manufactured/mto product.

        The production is set to be made in multiple steps (PBM & SAM)

        A production order is created.
        Increasing the quantity to sell should create another manufacturing order with the delta quantity."""
        self.warehouse_1.manufacture_steps = 'pbm_sam'
        so = self._create_sale_order()

        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])
        pbm_move = mo.move_raw_ids.move_orig_ids.filtered(lambda m: m.product_id == self.component1)
        sam_move = mo.move_finished_ids.move_dest_ids
        self.assertEqual(len(pbm_move), 1)
        self.assertEqual(len(sam_move), 1)

        so_form = Form(so)
        with so_form.order_line.edit(0) as line:
            line.product_uom_qty = 8
        so = so_form.save()

        mos = self.env['mrp.production'].search([
            ('product_id', '=', self.product_manu.id),
            ('state', '=', 'confirmed'),
        ])
        self.assertEqual(len(mos), 2)
        self.assertEqual(sum(mos.mapped('product_qty')), 8)

        pbm_move_extra = mos[1].move_raw_ids.filtered(lambda m: m.product_id == self.component1)
        sam_move_extra = mos[1].move_finished_ids
        self.assertEqual(pbm_move_extra.product_uom_qty, 3)
        self.assertEqual(sam_move_extra.product_uom_qty, 3)
        self.assertEqual(mos[1].move_raw_ids.filtered(lambda m: m.product_id == self.component1).product_uom_qty, 3)
