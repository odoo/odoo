# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import OrderedDict

from lxml import etree

from odoo.fields import Command
from odoo.tests import HttpCase, TransactionCase, loaded_demo_data, tagged


_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestWebsiteSaleComparison(TransactionCase):

    def test_01_website_sale_comparison_remove(self):
        """ This tour makes sure the product page still works after the module
        `website_sale_comparison` has been removed.

        Technically it tests the removal of copied views by the base method
        `_remove_copied_views`. The problematic view that has to be removed is
        `product_attributes_body` because it has a reference to `add_to_compare`.
        """
        Website0 = self.env['website'].with_context(website_id=None)
        Website1 = self.env['website'].with_context(website_id=1)

        # Create a generic inherited view, with a key not starting with
        # `website_sale_comparison` otherwise the unlink will work just based on
        # the key, but we want to test also for `MODULE_UNINSTALL_FLAG`.
        product_attributes_body = Website0.viewref('website_sale_comparison.product_attributes_body')
        test_view_key = 'my_test.my_key'
        self.env['ir.ui.view'].with_context(website_id=None).create({
            'name': 'test inherited view',
            'key': test_view_key,
            'inherit_id': product_attributes_body.id,
            'arch': '<div/>',
        })

        # Retrieve the generic view
        product = Website0.viewref('website_sale.product')
        # Trigger COW to create specific views of the whole tree
        product.with_context(website_id=1).write({'name': 'Trigger COW'})

        # Verify initial state: the specific views exist
        self.assertEqual(Website1.viewref('website_sale.product').website_id.id, 1)
        self.assertEqual(Website1.viewref('website_sale_comparison.product_attributes_body').website_id.id, 1)
        self.assertEqual(Website1.viewref(test_view_key).website_id.id, 1)

        # Remove the module (use `module_uninstall` because it is enough to test
        # what we want here, no need/can't use `button_immediate_uninstall`
        # because it would commit the test transaction)
        website_sale_comparison = self.env['ir.module.module'].search([('name', '=', 'website_sale_comparison')])
        website_sale_comparison.module_uninstall()

        # Check that the generic view is correctly removed
        self.assertFalse(Website0.viewref('website_sale_comparison.product_attributes_body', raise_if_not_found=False))
        # Check that the specific view is correctly removed
        self.assertFalse(Website1.viewref('website_sale_comparison.product_attributes_body', raise_if_not_found=False))

        # Check that the generic inherited view is correctly removed
        self.assertFalse(Website0.viewref(test_view_key, raise_if_not_found=False))
        # Check that the specific inherited view is correctly removed
        self.assertFalse(Website1.viewref(test_view_key, raise_if_not_found=False))


@tagged('post_install', '-at_install')
class TestWebsiteSaleComparisonUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.attribute_varieties = cls.env['product.attribute'].create({
            'name': 'Grape Varieties',
            'sequence': 2,
            'value_ids': [
                Command.create({
                    'name': n,
                    'sequence': i,
                }) for i, n in enumerate(['Cabernet Sauvignon', 'Merlot', 'Cabernet Franc', 'Petit Verdot'])
            ],
        })
        cls.attribute_vintage = cls.env['product.attribute'].create({
            'name': 'Vintage',
            'sequence': 1,
            'value_ids': [
                Command.create({
                    'name': n,
                    'sequence': i,
                }) for i, n in enumerate(['2018', '2017', '2016', '2015'])
            ],
        })
        cls.values_varieties = cls.attribute_varieties.value_ids
        cls.values_vintage = cls.attribute_vintage.value_ids
        cls.template_margaux = cls.env['product.template'].create({
            'name': "Château Margaux",
            'website_published': True,
            'list_price': 0,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.attribute_vintage.id,
                    'value_ids': [Command.set(cls.values_vintage.ids)]
                })
            ]
        })
        cls.attribute_line_vintage = cls.template_margaux.attribute_line_ids
        cls.attribute_line_varieties = cls.env['product.template.attribute.line'].create([{
            'product_tmpl_id': cls.template_margaux.id,
            'attribute_id': cls.attribute_varieties.id,
            'value_ids': [(6, 0, v.ids)],
        } for v in cls.values_varieties])
        cls.variants_margaux = cls.template_margaux._get_possible_variants_sorted()

        for variant, price in zip(cls.variants_margaux, [487.32, 394.05, 532.44, 1047.84]):
            variant.product_template_attribute_value_ids.filtered(lambda ptav: ptav.attribute_id == cls.attribute_vintage).price_extra = price

    def test_01_admin_tour_product_comparison(self):
        attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 10,
            'display_type': 'color',
            'value_ids': [
                Command.create({
                    'name': 'Red',
                }),
                Command.create({
                    'name': 'Pink',
                }),
                Command.create({
                    'name': 'Blue'
                })
            ]
        })
        self.env['product.template'].create([{
            'name': 'Color T-Shirt',
            'list_price': 20.0,
            'website_sequence': 1,
            'is_published': True,
            'type': 'service',
            'invoice_policy': 'delivery',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids,
                })
            ]
        }, {
            'name': 'Color Pants',
            'list_price': 20.0,
            'website_sequence': 1,
            'is_published': True,
            'type': 'service',
            'invoice_policy': 'delivery',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids,
                })
            ]
        }, {
            'name': 'Color Shoes',
            'list_price': 20.0,
            'website_sequence': 1,
            'is_published': True,
            'type': 'service',
            'invoice_policy': 'delivery',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids,
                })
            ]
        }])
        self.start_tour("/", 'product_comparison', login='admin')

    def test_02_attribute_multiple_lines(self):
        # Case product page with "Product attributes table" disabled (website_sale standard case)
        self.env['website'].viewref('website_sale_comparison.product_attributes_body').active = False
        res = self.url_open('/shop/%d' % self.template_margaux.id)
        self.assertEqual(res.status_code, 200)
        root = etree.fromstring(res.content, etree.HTMLParser())

        tr_varieties_simple_att = root.xpath('//div[@id="product_attributes_simple"]//tr')[0]
        text = etree.tostring(tr_varieties_simple_att, encoding='unicode', method='text')
        self.assertEqual(text.replace(' ', '').replace('\n', ''), "GrapeVarieties:CabernetSauvignon,Merlot,CabernetFranc,PetitVerdot")

        # Case product page with "Product attributes table" enabled
        self.env['website'].viewref('website_sale_comparison.product_attributes_body').active = True
        res = self.url_open('/shop/%d' % self.template_margaux.id)
        self.assertEqual(res.status_code, 200)
        root = etree.fromstring(res.content, etree.HTMLParser())

        tr_vintage = root.xpath('//div[@id="product_specifications"]//tr')[0]
        text_vintage = etree.tostring(tr_vintage, encoding='unicode', method='text')
        self.assertEqual(text_vintage.replace(' ', '').replace('\n', ''), "Vintage2018,2017,2016,2015")

        tr_varieties = root.xpath('//div[@id="product_specifications"]//tr')[1]
        text_varieties = etree.tostring(tr_varieties, encoding='unicode', method='text')
        self.assertEqual(text_varieties.replace(' ', '').replace('\n', ''), "GrapeVarietiesCabernetSauvignon,Merlot,CabernetFranc,PetitVerdot")

        # Case compare page
        res = self.url_open('/shop/compare?products=%s' % ','.join(str(id) for id in self.variants_margaux.ids))
        self.assertEqual(res.status_code, 200)
        root = etree.fromstring(res.content, etree.HTMLParser())

        table = root.xpath('//div[@id="o_comparelist_table"]')[0]

        products = table.xpath('//div[@id="o_comparelist_product_name"]/a/h6')
        self.assertEqual(len(products), 4)
        for product, name in zip(products, ['ChâteauMargaux(2018)', 'ChâteauMargaux(2017)', 'ChâteauMargaux(2016)', 'ChâteauMargaux(2015)']):
            text = etree.tostring(product, encoding='unicode', method='text')
            self.assertEqual(text.replace(' ', '').replace('\n', ''), name)

        attribute_vintage = table.xpath('//div[@id="o_comparelist_attribute"]')[0]
        text_vintage = etree.tostring(attribute_vintage, encoding='unicode', method='text')
        self.assertEqual(text_vintage.replace(' ', '').replace('\n', ''), "Vintage2018")

        attribute_varieties = table.xpath('//div[@id="o_comparelist_attribute"]')[4]
        text_varieties = etree.tostring(attribute_varieties, encoding='unicode', method='text')
        self.assertEqual(text_varieties.replace(' ', '').replace('\n', ''), "GrapeVarietiesCabernetSauvignon,Merlot,CabernetFranc,PetitVerdot")

    def test_03_category_order(self):
        """Test that categories are shown in the correct order when the
        attributes are in a different order."""
        category_vintage = self.env['product.attribute.category'].create({
            'name': 'Vintage',
            'sequence': 2,
        })
        category_varieties = self.env['product.attribute.category'].create({
            'name': 'Varieties',
            'sequence': 1,
        })
        self.attribute_vintage.category_id = category_vintage
        self.attribute_varieties.category_id = category_varieties

        prep_categories = self.template_margaux.valid_product_template_attribute_line_ids._prepare_categories_for_display()
        self.assertEqual(prep_categories, OrderedDict([
            (category_varieties, self.attribute_line_varieties),
            (category_vintage, self.attribute_line_vintage),
        ]))

        variant_margaux = self.template_margaux.product_variant_id
        variant_ptavs = variant_margaux.product_template_attribute_value_ids

        prep_categories = self.variants_margaux[0]._prepare_categories_for_display()
        self.assertEqual(prep_categories, OrderedDict([
            (category_varieties, OrderedDict([
                (self.attribute_varieties, OrderedDict([
                    (variant_margaux, variant_ptavs.filtered(
                        lambda ptav: ptav.attribute_id == self.attribute_varieties
                    ))
                ]))
            ])),
            (category_vintage, OrderedDict([
                (self.attribute_vintage, OrderedDict([
                    (variant_margaux, variant_ptavs.filtered(
                        lambda ptav: ptav.attribute_id == self.attribute_vintage
                    ))
                ]))
            ])),
        ]))
