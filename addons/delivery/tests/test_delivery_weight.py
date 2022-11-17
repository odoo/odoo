from odoo.tests import common
from odoo.tools import float_round


@common.tagged('post_install', '-at_install')
class TestDeliveryWeight(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_kg = cls.env['product.product'].create({
            'name': 'Product in kg',
            'type': 'product',
            'weight': 4,
            'weight_uom_id': cls.env.ref('uom.product_uom_kgm').id
        })

        cls.product_lb = cls.env['product.product'].create({
            'name': 'Product in lb',
            'type': 'product',
            'weight': 4,
            'weight_uom_id': cls.env.ref('uom.product_uom_lb').id
        })

        cls.product_delivery = cls.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })

        cls.delivery_pack_type = cls.env['stock.package.type'].create({
            'name': "My Package",
            'base_weight': 1,
            'max_weight': 20,
            'weight_uom_id': cls.env.ref('uom.product_uom_lb').id
        })
        # carrier weight uom is kg and dimension uom is mm by default
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Delivery Carrier',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'product_id': cls.product_delivery.id,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Customer'})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.env['stock.quant']._update_available_quantity(cls.product_kg, cls.warehouse.lot_stock_id, 20)
        cls.env['stock.quant']._update_available_quantity(cls.product_lb, cls.warehouse.lot_stock_id, 20)

    def test_delivery_weight_conversions(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': 'kg product',
                'product_id': self.product_kg.id,
                'product_uom_qty': 2,
                'price_unit': 10,
            }), (0, 0, {
                'name': 'lb product',
                'product_id': self.product_lb.id,
                'product_uom_qty': 2,
                'price_unit': 10,
            })],
        })
        weight_kg = sale_order._get_estimated_weight()
        self.assertEqual(float_round(weight_kg, 2), 11.63)
        packages = self.carrier._get_packages_from_order(sale_order, self.delivery_pack_type)
        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0].weight, 20)
        self.assertEqual(packages[0].weight_uom_id, self.env.ref('uom.product_uom_lb'))
        total_package_weight = sum(pack.weight for pack in packages)
        order_weight_in_pounds = sale_order._get_estimated_weight(self.delivery_pack_type.weight_uom_id) + self.delivery_pack_type.base_weight
        self.assertEqual(total_package_weight, order_weight_in_pounds)
        delivery_wizard = self.env['choose.delivery.carrier'].with_context({
            'order_id': sale_order.id,
            'carrier_id': self.carrier.id
        })
        delivery_wizard.button_confirm()
        sale_order.action_confirm()
        # Ship
        for ml in sale_order.picking_ids.move_ids.move_line_ids:
            ml.qty_done = 2
        picking_id = sale_order.picking_ids
        picking_id.button_validate()
        packages = self.carrier._get_packages_from_picking(picking_id, self.delivery_pack_type)
        total_package_weight = sum(pack.weight for pack in packages)
        # TODO: fix pricision errors, should be 11.63
        self.assertEqual(picking_id.shipping_weight, 11.64)
        self.assertEqual(picking_id.weight_bulk, 11.64)
