from openerp.tests.common import TransactionCase

class TestOnchangeProductId(TransactionCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    def setUp(self):
        super(TestOnchangeProductId, self).setUp()
        self.fiscal_position_model = self.env['account.fiscal.position']
        self.fiscal_position_tax_model = self.env['account.fiscal.position.tax']
        self.tax_model = self.env['account.tax']
        self.so_model = self.env['sale.order']
        self.po_line_model = self.env['sale.order.line']
        self.res_partner_model = self.env['res.partner']
        self.product_tmpl_model = self.env['product.template']
        self.product_model = self.env['product.product']
        self.product_uom_model = self.env['product.uom']
        self.supplierinfo_model = self.env["product.supplierinfo"]
        self.pricelist_model = self.env['product.pricelist']

    def test_onchange_product_id(self):

        uom_id = self.product_uom_model.search([('name', '=', 'Unit(s)')])[0]
        pricelist = self.pricelist_model.search([('name', '=', 'Public Pricelist')])[0]

        partner_id = self.res_partner_model.create(dict(name="George"))
        tax_include_id = self.tax_model.create(dict(name="Include tax",
                                                    amount='21.00',
                                                    price_include=True,
                                                    type_tax_use='sale'))
        tax_exclude_id = self.tax_model.create(dict(name="Exclude tax",
                                                    amount='0.00',
                                                    type_tax_use='sale'))

        product_tmpl_id = self.product_tmpl_model.create(dict(name="Voiture",
                                                              list_price=121,
                                                              taxes_id=[(6, 0, [tax_include_id.id])]))

        product_id = self.product_model.create(dict(product_tmpl_id=product_tmpl_id.id))

        fp_id = self.fiscal_position_model.create(dict(name="fiscal position", sequence=1))

        fp_tax_id = self.fiscal_position_tax_model.create(dict(position_id=fp_id.id,
                                                               tax_src_id=tax_include_id.id,
                                                               tax_dest_id=tax_exclude_id.id))
        so_vals = {
            'partner_id': partner_id.id,
            'pricelist_id': pricelist.id,
            'fiscal_position_id': fp_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_uom_qty': 1.0,
                    'product_uom': uom_id.id,
                    'price_unit': 121.0
                })
            ]
        }

        so = self.so_model.create(so_vals)

        so_line = so.order_line[0]
        so_line.product_id_change()
        self.assertEquals(100, so_line.price_unit, "The included tax must be subtracted to the price")

    def test_pricelist_application(self):
        """ Test different prices are correctly applied based on dates """
        support_product = self.env.ref('product.product_product_2')
        support_product.list_price = 100
        partner = self.res_partner_model.create(dict(name="George"))

        christmas_pricelist = self.env['product.pricelist'].create({
            'name': 'Christmas pricelist',
            'item_ids': [(0, 0, {
                'date_start': "2017-12-01",
                'date_end': "2017-12-24",
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 20,
                'applied_on': '3_global',
                'name': 'Pre-Christmas discount'
            }), (0, 0, {
                'date_start': "2017-12-25",
                'date_end': "2017-12-31",
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 50,
                'applied_on': '3_global',
                'name': 'Post-Christmas super-discount'
            })]
        })

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': '2017-12-20',
            'pricelist_id': christmas_pricelist.id,
        })

        order_line = self.env['sale.order.line'].new({
            'order_id': so.id,
            'product_id': support_product.id,
        })

        # force compute uom and prices
        order_line.product_id_change()
        order_line.product_uom_change()

        self.assertEqual(order_line.price_unit, 80, "First date pricelist rule not applied")

        so.date_order = '2017-12-30'
        order_line.product_id_change()
        self.assertEqual(order_line.price_unit, 50, "Second date pricelist rule not applied")
