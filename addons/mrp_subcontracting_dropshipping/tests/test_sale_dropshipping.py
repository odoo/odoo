from odoo.tests import Form
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSaleDropshippingFlows(TestMrpSubcontractingCommon):
    
    def test_dropship_with_different_uom(self):
        """This test checks the flow when we add a sale order
        for a product with a bom which contains two components
        with two differents UoM, save it, and then
        modify the quantity. This test is here instead of
        stock_dropshipping, in order to be able to use
        mrp.bom, which is not a dependency of stock_dropshipping.
        """

        location = self.env.ref('stock.stock_location_stock')

        # Create a vendor
        supplier_dropship = self.env['res.partner'].create({'name': 'Vendor of Dropshipping test'})

        # Create a product
        test_product = self.env['product.template'].create({"name": "Product"})

        # Create a component with UoM Liters with dropshipping route
        dropshipping_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        component_liter = self.env['product.template'].create({
            "name": "component liter",
            "route_ids": [(6, 0, [dropshipping_route.id])],
            "seller_ids": [(0, 0, {
                'delay': 1,
                'name': supplier_dropship.id,
                'min_qty': 1.0
            })],
            "uom_id": 11,
            "uom_po_id": 11,
        })

        # Create an other component with UoM Units without dropshipping route
        component_unit = self.env['product.template'].create({
            "name": "component liter",
            "type": "product",
            "uom_id": 1,
            "uom_po_id": 1,
        })

        self.env['stock.quant']._update_available_quantity(component_unit.product_variant_id, location, 100)

        # Create a BoM for the product with the two components
        self.env['mrp.bom'].create({
            "product_tmpl_id": test_product.id,
            "product_id": False,
            "product_qty": 1,
            "type": "phantom",
            "bom_line_ids": [
                [0, 0, {"product_id": component_liter.product_variant_id.id, "product_qty": 1}],
                [0, 0, {"product_id": component_unit.product_variant_id.id, "product_qty": 1}],
            ]
        })

        # Create a sales order with a line of 1 test_product
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_2')
        so_form.payment_term_id = self.env.ref('account.account_payment_term_end_following_month')
        with so_form.order_line.new() as line:
            line.product_id = test_product.product_variant_id
            line.product_uom_qty = 1
            line.price_unit = 1.00
        sale_order = so_form.save()
        sale_order.action_confirm()

        # Modify the quantity on sale order line
        sale_order.write({'order_line': [[1, sale_order.order_line.id, {'product_uom_qty': 2.00}]]})

        self.assertEqual(sale_order.order_line.product_uom_qty, 2)
