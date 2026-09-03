from odoo.tests import Form
from odoo.addons.stock.tests.common import TestStockCommon


class TestMrpReportMoOverview(TestStockCommon):
    _test_user_groups = (
        'base.group_user',
        'mrp.group_mrp_manager',
        'mrp.group_mrp_routings',  # view visibility (duration/workorder fields) granted to cls.env.user in Common
        'mrp.group_mrp_byproducts',  # view visibility (byproducts) granted to mrp users in Common
        'stock.group_stock_manager',  # setup: warehouse/route/rule/orderpoint/location/picking_type config in test bodies
        'uom.group_uom',  # view visibility (uom_id) granted to cls.env.user in Common
        'purchase.group_purchase_user',  # confirmation of the PO
    )

    _test_user_name = 'Test Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.route_buy = cls.env.ref('purchase_stock.route_warehouse0_buy')
        cls.route_mto = cls.env.ref('stock.route_warehouse0_mto')

        cls.vendor = cls.env['res.partner'].create({'name': 'Subcontractor Vendor'})

        cls.comp_1 = cls.env['product.product'].create({
            'name': 'Component 1',
            'is_storable': True,
            'standard_price': 15.0,
        })
        cls.comp_2 = cls.env['product.product'].create({
            'name': 'Component 2',
            'is_storable': True,
            'standard_price': 25.0,
        })

        cls.sub_product = cls.env['product.product'].create({
            'name': 'Subcontracted Product',
            'is_storable': True,
            'route_ids': [(6, 0, [cls.route_buy.id, cls.route_mto.id])],
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
                'min_qty': 1.0,
                'price': 100.0,
            })],
            'standard_price': 40.0,
        })

        cls.sub_bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.sub_product.product_tmpl_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, [cls.vendor.id])],
            'bom_line_ids': [
                (0, 0, {'product_id': cls.comp_1.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': cls.comp_2.id, 'product_qty': 1.0}),
            ]
        })

        cls.final_product = cls.env['product.product'].create({
            'name': 'Final Product',
        })
        cls.final_bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': cls.sub_product.id, 'product_qty': 2.0})]
        })

    def test_subcontracted_product_mo_cost(self):
        # create and confirm MO
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.final_product
        mo_form.bom_id = self.final_bom
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()

        # replenish the product
        replenish_wizard = self.env['product.replenish'].with_context(
            default_product_tmpl_id=self.sub_product.product_tmpl_id.id,
        ).create({
            'route_id': self.route_buy.id,
            'quantity': 2,
            'product_id': self.sub_product.id,
        })
        replenish_wizard.launch_replenishment()

        # find the move line
        po_line = self.env['purchase.order.line'].search([
            ('product_id', '=', self.sub_product.id),
            ('order_id.partner_id', '=', self.vendor.id)
        ], limit=1)

        # verify cost
        report = self.env['report.mrp.report_mo_overview']
        result_before_confirm = report._get_components_data(mo, level=1, current_index='')
        self.assertEqual(result_before_confirm[0]['summary']['mo_cost'], 280.0)

        # confirm the purchase order
        po_line.order_id.button_confirm()

        # verify cost after PO confirmation
        result_after_confirm = report._get_components_data(mo, level=1, current_index='')
        self.assertEqual(result_after_confirm[0]['summary']['mo_cost'], 280.0)
