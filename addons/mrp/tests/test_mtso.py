from odoo.addons.stock.tests.test_mtso import TestStockMtso


class TestMrpMtso(TestStockMtso):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MrpProduction = cls.env['mrp.production']

        cls.route_manufacture = cls.warehouse_1_step.manufacture_pull_id.route_id.id
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # products
        cls.finished_product = cls.ProductObj.create({
            'name': 'Product M',
            'type': 'product',
            'route_ids': [(4, cls.route_mtso), (4, cls.route_manufacture)],
        })
        cls.consu_raw = cls.ProductObj.create({
            'name': 'raw M',
            'type': 'consu',
        })

        # Create bom for finish product
        cls.env['mrp.bom'].create({
            'product_id': cls.finished_product.id,
            'product_tmpl_id': cls.finished_product.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(5, 0), (0, 0, {'product_id': cls.consu_raw.id})]
        })
