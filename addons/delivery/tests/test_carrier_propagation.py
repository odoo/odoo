from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestCarrierPropagation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # For performances reasons
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.warehouse = cls.env.ref("stock.warehouse0")

        # Set Warehouse as multi steps delivery
        cls.warehouse.delivery_steps = "pick_pack_ship"

        # Create a delivery product and its carrier
        cls.ProductProduct = cls.env['product.product']
        cls.SaleOrder = cls.env['sale.order']
        cls.StockMove = cls.env["stock.move"]

        cls.partner_propagation = cls.env['res.partner'].create({
            'name': 'My Carrier Propagation Customer'})

        cls.product_uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product_delivery_normal = cls.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })
        cls.normal_delivery = cls.env['delivery.carrier'].create({
            'name': 'Normal Delivery Charges',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'product_id': cls.product_delivery_normal.id,
        })
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.output_location = cls.env.ref("stock.stock_location_output")
        cls.super_product = cls.ProductProduct.create({
            'name': 'Super Product',
            'invoice_policy': 'delivery',
        })
        mto_route = cls.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        cls.warehouse.mto_pull_id.procure_method = "make_to_stock"
        cls.mto_product = cls.ProductProduct.create({
            'name': 'MTO Product',
            'invoice_policy': 'delivery',
            'route_ids': [(6, 0, mto_route.ids)],
        })
        cls.rule_pack = cls.env["procurement.group"]._get_rule(
            cls.super_product, cls.output_location, {"warehouse_id": cls.warehouse})

    def test_carrier_no_propagation(self):
        """
            Set the carrier propagation to False on stock.rule
            Create a Sale Order, confirm it
            Check that the carrier is set on the OUT
            Check that the carrier is not set on the PACK
        """
        self.rule_pack.propagate_carrier = False

        so = self.SaleOrder.create({
            'name': 'Sale order',
            'partner_id': self.partner_propagation.id,
            'partner_invoice_id': self.partner_propagation.id,
            'order_line': [
                (0, 0, {'name': self.super_product.name, 'product_id': self.super_product.id, 'product_uom_qty': 1, 'price_unit': 1,}),
            ]
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        # Confirm the SO
        so.action_confirm()
        move_out = self.StockMove.search([("location_dest_id.usage", "=", "customer"), ("product_id", "=", self.super_product.id)])
        self.assertEqual(
            self.normal_delivery,
            move_out.picking_id.carrier_id,
        )
        move_pack = self.StockMove.search([("move_dest_ids", "in", move_out.ids)])

        self.assertFalse(move_pack.picking_id.carrier_id)

    def test_carrier_propagation(self):
        """
            Set the carrier propagation to True on stock.rule
            Create a Sale Order, confirm it
            Check that the carrier is set on the OUT
            Check that the carrier is set on the PACK
        """
        self.rule_pack.propagate_carrier = True

        for product in [self.super_product, self.mto_product]:
            so = self.SaleOrder.create({
                'name': 'Sale order',
                'partner_id': self.partner_propagation.id,
                'partner_invoice_id': self.partner_propagation.id,
                'order_line': [
                    (0, 0, {'name': product.name, 'product_id': product.id, 'product_uom_qty': 1, 'price_unit': 1,}),
                ]
            })
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': so.id,
                'default_carrier_id': self.normal_delivery.id,
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()
            # Confirm the SO
            so.action_confirm()
            move_out = self.StockMove.search([("location_dest_id.usage", "=", "customer"), ("product_id", "=", product.id)])
            self.assertEqual(
                self.normal_delivery,
                move_out.picking_id.carrier_id,
            )
            move_pack = self.StockMove.search([("move_dest_ids", "in", move_out.ids)])
            self.assertEqual(
                self.normal_delivery,
                move_pack.picking_id.carrier_id,
        )
