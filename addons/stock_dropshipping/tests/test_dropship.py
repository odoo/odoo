from odoo.tests.common import TransactionCase


class TestDropship(TransactionCase):
    def test_change_qty(self):
        # enable the dropship and MTO route on the product
        prod = self.env.ref('product.product_product_8')
        dropshipping_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        prod.write({'route_ids': [(6, 0, [dropshipping_route.id, mto_route.id])]})

        # add a vendor
        vendor1 = self.env['res.partner'].create({'name': 'vendor1'})
        seller1 = self.env['product.supplierinfo'].create({
            'name': vendor1.id,
            'price': 8,
        })
        prod.write({'seller_ids': [(6, 0, [seller1.id])]})

        # sell one unit of this product
        cust = self.env['res.partner'].create({'name': 'customer1'})
        so = self.env['sale.order'].create({
            'partner_id': cust.id,
            'partner_invoice_id': cust.id,
            'partner_shipping_id': cust.id,
            'order_line': [(0, 0, {
                'name': prod.name,
                'product_id': prod.id,
                'product_uom_qty': 1.00,
                'product_uom': prod.uom_id.id,
                'price_unit': 12,
            })],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        so.action_confirm()
        po = self.env['purchase.order'].search([('group_id', '=', so.procurement_group_id.id)])
        po_line = po.order_line

        # Check the qty on the P0
        self.assertAlmostEqual(po_line.product_qty, 1.00)

        # Update qty on SO and check PO
        so.order_line.product_uom_qty = 2.00
        self.assertAlmostEqual(po_line.product_qty, 2.00)
