"""
Benchmark based on the `sale_mrp` addons (in `sale_mrp/test/sale_mrp.yml`).
"""

import time

from .benchmarks import Bench

class BenchSaleMrp(Bench):
    """\
    Similar to `sale_mrp/test/sale_mrp.yml`.

    This benchmarks the OpenERP server `sale_mrp` module by creating and
    confirming a sale order. As it creates data in the server, it is necessary
    to ensure unique names for the newly created data. You can use the --seed
    argument to give a lower bound to those names. (The number of generated
    names is --jobs * --samples.)
    """

    command_name = 'bench-sale-mrp'
    bench_name = '`sale_mrp/test/sale_mrp.yml`'

    def measure_once(self, i):
        if self.worker >= 0:
            i = int(self.args.seed) + i + (self.worker * int(self.args.samples))
        else:
            i = int(self.args.seed) + i

        # Resolve a few external-ids (this has little impact on the running
        # time of the whole method).
        product_uom_unit = self.execute('ir.model.data', 'get_object_reference', 'product', 'product_uom_unit')[1]
        my_slider_mobile_0 = self.execute('ir.model.data', 'get_object_reference', 'bench_sale_mrp', 'my_slider_mobile_0')[1]
        res_partner_4 = self.execute('ir.model.data', 'get_object_reference', 'base', 'res_partner_4')[1]
        res_partner_address_7 = self.execute('ir.model.data', 'get_object_reference', 'base', 'res_partner_address_7')[1]
        list0 = self.execute('ir.model.data', 'get_object_reference', 'product', 'list0')[1]
        shop = self.execute('ir.model.data', 'get_object_reference', 'sale', 'shop')[1]

        # Create a sale order for the product `Slider Mobile`.
        data = {
            'client_order_ref': 'ref_xxx_' + str(i).rjust(6, '0'),
            'date_order': time.strftime('%Y-%m-%d'),
            'invoice_quantity': 'order',
            'name': 'sale_order_ref_xxx_' + str(i).rjust(6, '0'),
            'order_line': [(0, 0, {
                'name': 'Slider Mobile',
                'price_unit': 2,
                'product_uom': product_uom_unit,
                'product_uom_qty': 5.0,
                'state': 'draft',
                'delay': 7.0,
                'product_id': my_slider_mobile_0,
                'product_uos_qty': 5,
                'type': 'make_to_order',
            })],
            'order_policy': 'manual',
            'partner_id': res_partner_4,
            'partner_invoice_id': res_partner_address_7,
            'partner_order_id': res_partner_address_7,
            'partner_shipping_id': res_partner_address_7,
            'picking_policy': 'direct',
            'pricelist_id': list0,
            'shop_id': shop,
        }
        sale_order_id = self.execute('sale.order', 'create', data, {})

        # Confirm the sale order.
        self.object_proxy.exec_workflow(self.database, self.uid, self.password, 'sale.order', 'order_confirm', sale_order_id, {})

