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
        res = delivery.button_validate()
        Form(self.env['stock.immediate.transfer'].with_context(res['context'])).save().process()

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
        sbc_location = self.env.company.subcontracting_location_id
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
        return_form.location_id = sbc_location
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 1
        return_wizard = return_form.save()
        return_id, _ = return_wizard._create_returns()
        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_lines.quantity_done = 1
        return_picking.button_validate()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 0.0,   'credit': 110.0},
            {'account_id': stock_in_acc_id,     'product_id': self.product_a.id,    'debit': 110.0, 'credit': 0.0},
        ])

        # return to stock location
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        stock_location.return_location = True
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
        return_form.location_id = stock_location
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 1
        return_wizard = return_form.save()
        return_id, _ = return_wizard._create_returns()
        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_lines.quantity_done = 1
        return_picking.button_validate()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_out_acc_id,    'product_id': self.product_a.id,    'debit': 0.0,   'credit': 110.0},
            {'account_id': stock_valu_acc_id,   'product_id': self.product_a.id,    'debit': 110.0, 'credit': 0.0},
        ])
