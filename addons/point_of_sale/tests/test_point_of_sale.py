# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPointOfSale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ignore pre-existing pricelists for the purpose of this test
        cls.env["product.pricelist"].search([]).write({"active": False})

        cls.currency = cls.env.ref("base.USD")
        cls.company1, cls.company2 = cls.env["res.company"].create([{
            "name": "company 1",
            "currency_id": cls.currency.id
        }, {
            "name": "company 2",
            "currency_id": cls.currency.id
        }])
        cls.company2_pricelist = cls.env["product.pricelist"].create({
            "name": "company 2 pricelist",
            "currency_id": cls.currency.id,
            "company_id": cls.company2.id,
            "sequence": 1,  # force this pricelist to be first
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Bank',
            'type': 'bank',
            'company_id': cls.company1.id,
            'code': 'BNK',
            'sequence': 11,
        })

        cls.env.user.company_id = cls.company1

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

        # Cannot archive config while session is active
        with self.assertRaises(UserError):
            config.write({'active': False})

    def test_pos_category_display_name_translated(self):
        self.env['res.lang']._activate_lang('fr_FR')
        parent = self.env['pos.category'].create({'name': 'Food'})
        child = self.env['pos.category'].create({'name': 'Fries', 'parent_id': parent.id})
        parent.update_field_translations('name', {'fr_FR': 'Nourriture'})
        child.update_field_translations('name', {'fr_FR': 'Frites'})
        # store complete_name in English
        self.env.flush_all()

        self.assertEqual(child.with_context(lang='en_US').display_name, 'Food / Fries')
        self.assertEqual(child.with_context(lang='fr_FR').display_name, 'Nourriture / Frites')

        PosCategory = self.env['pos.category'].with_context(lang='fr_FR')
        self.assertEqual(PosCategory.name_search('Frites'), [(child.id, 'Nourriture / Frites')])
        self.assertEqual(PosCategory.search([('display_name', 'ilike', 'Food / Fri')]), child)
