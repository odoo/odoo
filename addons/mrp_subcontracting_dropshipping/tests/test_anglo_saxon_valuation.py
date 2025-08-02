# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo import Command
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSubcontractingDropshippingValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        categ_form = Form(cls.env['product.category'])
        categ_form.name = 'fifo auto'
        categ_form.parent_id = cls.env.ref('product.product_category_all')
        categ_form.property_cost_method = 'fifo'
        categ_form.property_valuation = 'real_time'
        cls.categ_fifo_auto = categ_form.save()

        categ_form = Form(cls.env['product.category'])
        categ_form.name = 'avco auto'
        categ_form.parent_id = cls.env.ref('product.product_category_all')
        categ_form.property_cost_method = 'average'
        categ_form.property_valuation = 'real_time'
        cls.categ_avco_auto = categ_form.save()

        (cls.product_a | cls.product_b).is_storable = True

        cls.dropship_route = cls.env.ref('stock_dropshipping.route_drop_shipping')
        cls.dropship_subcontractor_route = cls.env.ref('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping')

        cls.bom_a = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_a.product_tmpl_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, cls.partner_a.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_b.id, 'product_qty': 1.0}),
            ],
        })

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

        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})

        (self.product_a | self.product_b).categ_id = self.categ_fifo_auto
        self.product_b.standard_price = 10

        dropship_picking_type = self.env['stock.picking.type'].search([
            ('company_id', '=', self.env.company.id),
            ('default_location_src_id.usage', '=', 'supplier'),
            ('default_location_dest_id.usage', '=', 'customer'),
        ], limit=1, order='sequence')

        po = self.env['purchase.order'].create({
            "partner_id": self.partner_a.id,
            "picking_type_id": dropship_picking_type.id,
            "dest_address_id": self.partner_b.id,
            "order_line": [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_qty': 2.0,
                'price_unit': 100,
                'taxes_id': False,
            })],
        })
        po.button_confirm()

        delivery = po.picking_ids
        delivery.button_validate()

        stock_in_acc_id = self.categ_fifo_auto.property_stock_account_input_categ_id.id
        stock_out_acc_id = self.categ_fifo_auto.property_stock_account_output_categ_id.id
        stock_valu_acc_id = self.categ_fifo_auto.property_stock_valuation_account_id.id
        stock_cop_acc_id = self.categ_fifo_auto.property_stock_account_production_cost_id.id

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            # Compensation of dropshipping value
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 20.0,  'credit': 0.0},
            # Receipt from subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 220.0, 'credit': 0.0},
            {'account_id': stock_in_acc_id,     'product_id': self.product_a.id,    'debit': 0.0,   'credit': 200.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.product_a.id,    'debit': 0.0,   'credit': 20.0},
            # Delivery to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.product_b.id,    'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.product_b.id,    'debit': 20.0,  'credit': 0.0},
            # Initial dropshipped value
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 0.0,   'credit': 200.0},
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 200.0, 'credit': 0.0},
        ])

        # return to subcontracting location
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 1
        return_wizard = return_form.save()
        return_picking = return_wizard._create_return()
        return_picking.move_ids.quantity = 1
        return_picking.move_ids.picked = True
        return_picking.button_validate()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_out_acc_id,      'product_id': self.product_a.id,    'debit': 0.0,   'credit': 110.0},
            {'account_id': stock_valu_acc_id,     'product_id': self.product_a.id,    'debit': 110.0, 'credit': 0.0},
        ])

        # return to stock location
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 1
        return_wizard = return_form.save()
        return_picking = return_wizard._create_return()
        return_picking.move_ids.quantity = 1
        return_picking.move_ids.picked = True
        return_picking.location_dest_id = stock_location
        return_picking.button_validate()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 0.0,   'credit': 110.0},
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 110.0, 'credit': 0.0},
        ])

    def test_avco_valuation_subcontract_and_dropshipped_and_backorder(self):
        """ Splitting a dropship transfer via backorder and invoicing for delivered quantities
        should result in SVL records which have accurate values based on the portion of the total
        order-picking sequence for which they were generated.
        """
        final_product = self.product_a
        final_product.write({
            'categ_id': self.categ_avco_auto.id,
            'invoice_policy': 'delivery',
        })
        comp_product = self.product_b
        comp_product.write({
            'categ_id': self.categ_avco_auto.id,
            'route_ids': [(4, self.dropship_subcontractor_route.id)],
        })

        self.env['product.supplierinfo'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'partner_id': self.partner_a.id,
            'price': 10,
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': comp_product.product_tmpl_id.id,
            'partner_id': self.partner_a.id,
            'price': 1,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': final_product.id,
                'route_id': self.dropship_route.id,
                'product_uom_qty': 100,
            })],
        })
        sale_order.action_confirm()
        purchase_order = sale_order._get_purchase_orders()[0]
        purchase_order.button_confirm()
        dropship_transfer = purchase_order.picking_ids[0]
        dropship_transfer.move_ids[0].quantity = 50
        dropship_transfer.with_context(cancel_backorder=False)._action_done()
        account_move_1 = sale_order._create_invoices()
        account_move_1.action_post()
        dropship_backorder = dropship_transfer.backorder_ids[0]
        dropship_backorder.move_ids[0].quantity = 50
        dropship_backorder._action_done()
        account_move_2 = sale_order._create_invoices()
        account_move_2.action_post()

        self.assertRecordValues(
            self.env['stock.valuation.layer'].search([('product_id', '=', final_product.id)]),
            [
                # DS/01
                {'reference': dropship_transfer.name, 'quantity': -50, 'value': -500},
                {'reference': dropship_transfer.move_ids.move_orig_ids[0].name, 'quantity': 50, 'value': 8500},
                {'reference': dropship_transfer.name, 'quantity': 0, 'value': -8000},
                # DS/02 - backorder
                {'reference': dropship_backorder.name, 'quantity': -50, 'value': -500},
                {'reference': dropship_backorder.move_ids.move_orig_ids[1].name, 'quantity': 50, 'value': 8500},
                {'reference': dropship_backorder.name, 'quantity': 0, 'value': -8000},
            ]
        )

    def test_account_line_entry_kit_bom_dropship(self):
        """ An order delivered via dropship for some kit bom product variant should result in
        accurate journal entries in the expense and stock output accounts if the cost on the
        purchase order line has been manually edited.
        """
        kit_final_prod = self.product_a
        product_c = self.env['product.product'].create({
            'name': 'product_c',
            'uom_id': self.env.ref('uom.product_uom_dozen').id,
            'uom_po_id': self.env.ref('uom.product_uom_dozen').id,
            'lst_price': 120.0,
            'standard_price': 100.0,
            'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
            'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
            'taxes_id': [Command.set((self.tax_sale_a + self.tax_sale_b).ids)],
            'supplier_taxes_id': [Command.set((self.tax_purchase_a + self.tax_purchase_b).ids)],
        })
        kit_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_final_prod.product_tmpl_id.id,
            'product_uom_id': kit_final_prod.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
        })
        kit_bom.bom_line_ids = [(0, 0, {
            'product_id': self.product_b.id,
            'product_qty': 4,
        }), (0, 0, {
            'product_id': product_c.id,
            'product_qty': 2,
        })]

        self.env['product.supplierinfo'].create({
            'product_id': self.product_b.id,
            'partner_id': self.partner_a.id,
            'price': 160,
        })
        self.env['product.supplierinfo'].create({
            'product_id': product_c.id,
            'partner_id': self.partner_a.id,
            'price': 100,
        })

        (kit_final_prod + self.product_b).categ_id.write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_b.id,
            'order_line': [(0, 0, {
                'price_unit': 900,
                'product_id': kit_final_prod.id,
                'route_id': self.dropship_route.id,
                'product_uom_qty': 2.0,
            })],
        })
        sale_order.action_confirm()
        purchase_order = sale_order._get_purchase_orders()[0]
        purchase_order.button_confirm()
        dropship_transfer = purchase_order.picking_ids[0]
        dropship_transfer.move_ids[0].quantity = 2.0
        dropship_transfer.button_validate()

        account_move = sale_order._create_invoices()
        account_move.action_post()

        # Each product_a should cost:
        # 4x product_b = 160 * 4 = 640 +
        # 2x product_c = 100 * 2 = 200
        #                        = 840
        self.assertRecordValues(
            account_move.line_ids.sorted('balance'),
            [
                {'name': 'product_a',                           'debit': 0.0,       'credit': 1800.0},
                {'name': 'product_a',                           'debit': 0.0,       'credit': 1680.0},
                {'name': '15% (Copy)',                          'debit': 0.0,       'credit': 270.0},
                {'name': f'{account_move.name} installment #1', 'debit': 621.0,     'credit': 0.0},
                {'name': f'{account_move.name} installment #2', 'debit': 1449.0,    'credit': 0.0},
                {'name': 'product_a',                           'debit': 1680.0,    'credit': 0.0},
            ]
        )
