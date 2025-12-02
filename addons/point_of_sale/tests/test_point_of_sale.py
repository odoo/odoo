# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import TransactionCase


class TestPointOfSale(TransactionCase):
    def setUp(self):
        super(TestPointOfSale, self).setUp()

        # ignore pre-existing pricelists for the purpose of this test
        self.env["product.pricelist"].search([]).write({"active": False})

        self.currency = self.env.ref("base.USD")
        self.company1 = self.env["res.company"].create({
            "name": "company 1",
            "currency_id": self.currency.id
        })
        self.company2 = self.env["res.company"].create({
            "name": "company 2",
            "currency_id": self.currency.id
        })
        self.company2_pricelist = self.env["product.pricelist"].create({
            "name": "company 2 pricelist",
            "currency_id": self.currency.id,
            "company_id": self.company2.id,
            "sequence": 1,  # force this pricelist to be first
        })
        self.bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'type': 'bank',
            'company_id': self.company1.id,
            'code': 'BNK',
            'sequence': 11,
        })

        self.env.user.company_id = self.company1

    def test_no_default_pricelist(self):
        """ Verify that the default pricelist isn't automatically set in the config """
        company1_pricelist = self.env["product.pricelist"].create({
            "name": "company 1 pricelist",
            "currency_id": self.currency.id,
            "company_id": self.company1.id,
            "sequence": 2,
        })

        # make sure this doesn't pick a pricelist as default
        new_config = self.env["pos.config"].create({
            "name": "usd config", "available_pricelist_ids": [(6, 0, [company1_pricelist.id])]
        })

        self.assertEqual(new_config.pricelist_id, self.env['product.pricelist'],
                         "POS config incorrectly has pricelist %s" % new_config.pricelist_id.display_name)

    def test_product_combo_variants(self):
        # Create product and combo
        product = self.env['product.product'].create({
            'name': 'Test Product 1',
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
        })

        product_combo = self.env["product.combo"].create(
            {
                "name": "Product combo",
                "combo_item_ids": [
                    Command.create({
                        "product_id": product.id,
                        "extra_price": 0,
                    }),
                ],
            }
        )
        # Add attribute and values, simulating variant creation
        size_attribute = self.env['product.attribute'].create({'name': 'Size'})
        attribute_value_1 = self.env['product.attribute.value'].create({'name': 'Large', 'attribute_id': size_attribute.id})
        attribute_value_2 = self.env['product.attribute.value'].create({'name': 'Small', 'attribute_id': size_attribute.id})
        original_product_id = product.id
        product_template = product.product_tmpl_id
        product.product_tmpl_id.with_context(create_product_product=True).write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [(6, 0, [attribute_value_1.id, attribute_value_2.id])],
            })],
        })
        # Check that original product should not be in combo anymore (replace by variants)
        self.assertTrue(original_product_id not in product_combo.combo_item_ids.mapped('product_id').ids, "Original product should not be in combo")

    def test_pos_bill_digits(self):
        coin = self.env["pos.bill"].create({
            "name": "0.005 not rounded",
            "value": 0.005
        })
        self.assertEqual(coin.value, 0.005)

    def test_pos_config_creates_warehouse(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        if warehouse:
            warehouse.write({'active': False, 'name': 'Archived ' + warehouse[0].name})
        pos_config = self.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
        })
        self.assertEqual(pos_config.warehouse_id.code, 'Sho')

    def test_session_filter_local_data(self):
        product1 = self.env['product.template'].create({
            'name': 'product1'
        })
        product2 = self.env['product.template'].create({
            'name': 'product2'
        })
        product3 = self.env['product.template'].create({
            'name': 'product3'
        })
        config = self.env["pos.config"].create({
            "name": "shop"
        })
        session = self.env['pos.session'].create({'name': 'Test Session', 'config_id': config.id})

        # Delete one product and archive another one
        products_to_display = [product1.id, product2.id, product3.id]
        product1.write({'active': False})
        product2.unlink()
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(products_to_display, [product3.id])

        # No change
        product4 = self.env['product.template'].create({
            'name': 'product4'
        })
        products_to_display = [product3.id, product4.id]
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(sorted(products_to_display), sorted([product3.id, product4.id]))

        # Delete all products
        products_to_display = [product3.id, product4.id]
        product3.unlink()
        product4.unlink()
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(products_to_display, [])
