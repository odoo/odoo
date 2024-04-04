# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from collections import OrderedDict
from lxml import etree
from odoo import tools

import odoo.tests

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('-at_install', 'post_install')
class TestWebsiteSaleComparison(odoo.tests.TransactionCase):
    def test_01_website_sale_comparison_remove(self):
        """ This tour makes sure the product page still works after the module
        `website_sale_comparison` has been removed.

        Technically it tests the removal of copied views by the base method
        `_remove_copied_views`. The problematic view that has to be removed is
        `product_attributes_body` because it has a reference to `add_to_compare`.
        """
        # YTI TODO: Adapt this tour without demo data
        # I still didn't figure why, but this test freezes on runbot
        # without the demo data
        if not odoo.tests.loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

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


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def setUp(self):
        super(TestUi, self).setUp()
        self.template_margaux = self.env['product.template'].create({
            'name': "Château Margaux",
            'website_published': True,
            'list_price': 0,
        })
        self.attribute_varieties = self.env['product.attribute'].create({
            'name': 'Grape Varieties',
            'sequence': 2,
        })
        self.attribute_vintage = self.env['product.attribute'].create({
            'name': 'Vintage',
            'sequence': 1,
        })
        self.values_varieties = self.env['product.attribute.value'].create({
            'name': n,
            'attribute_id': self.attribute_varieties.id,
            'sequence': i,
        } for i, n in enumerate(['Cabernet Sauvignon', 'Merlot', 'Cabernet Franc', 'Petit Verdot']))
        self.values_vintage = self.env['product.attribute.value'].create({
            'name': n,
            'attribute_id': self.attribute_vintage.id,
            'sequence': i,
        } for i, n in enumerate(['2018', '2017', '2016', '2015']))
        self.attribute_line_varieties = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': self.template_margaux.id,
            'attribute_id': self.attribute_varieties.id,
            'value_ids': [(6, 0, v.ids)],
        } for v in self.values_varieties])
        self.attribute_line_vintage = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.template_margaux.id,
            'attribute_id': self.attribute_vintage.id,
            'value_ids': [(6, 0, self.values_vintage.ids)],
        })
        self.variants_margaux = self.template_margaux._get_possible_variants_sorted()

        for variant, price in zip(self.variants_margaux, [487.32, 394.05, 532.44, 1047.84]):
            variant.product_template_attribute_value_ids.filtered(lambda ptav: ptav.attribute_id == self.attribute_vintage).price_extra = price

    def test_01_admin_tour_product_comparison(self):
        # YTI FIXME: Adapt to work without demo data
        if not odoo.tests.loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
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
        self.assertEqual(text_vintage.replace(' ', '').replace('\n', ''), "Vintage2018or2017or2016or2015")

        tr_varieties = root.xpath('//div[@id="product_specifications"]//tr')[1]
        text_varieties = etree.tostring(tr_varieties, encoding='unicode', method='text')
        self.assertEqual(text_varieties.replace(' ', '').replace('\n', ''), "GrapeVarietiesCabernetSauvignon,Merlot,CabernetFranc,PetitVerdot")

        # Case compare page
        res = self.url_open('/shop/compare?products=%s' % ','.join(str(id) for id in self.variants_margaux.ids))
        self.assertEqual(res.status_code, 200)
        root = etree.fromstring(res.content, etree.HTMLParser())

        table = root.xpath('//table[@id="o_comparelist_table"]')[0]

        products = table.xpath('//a[@class="o_product_comparison_table"]')
        self.assertEqual(len(products), 4)
        for product, name in zip(products, ['ChâteauMargaux(2018)', 'ChâteauMargaux(2017)', 'ChâteauMargaux(2016)', 'ChâteauMargaux(2015)']):
            text = etree.tostring(product, encoding='unicode', method='text')
            self.assertEqual(text.replace(' ', '').replace('\n', ''), name)

        tr_vintage = table.xpath('tbody/tr')[0]
        text_vintage = etree.tostring(tr_vintage, encoding='unicode', method='text')
        self.assertEqual(text_vintage.replace(' ', '').replace('\n', ''), "Vintage2018,2017,2016,20152018,2017,2016,20152018,2017,2016,20152018,2017,2016,2015")

        tr_varieties = table.xpath('tbody/tr')[1]
        text_varieties = etree.tostring(tr_varieties, encoding='unicode', method='text')
        self.assertEqual(text_varieties.replace(' ', '').replace('\n', ''), "GrapeVarieties" + 4 * "CabernetSauvignon,Merlot,CabernetFranc,PetitVerdot")

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

        prep_categories = self.variants_margaux[0]._prepare_categories_for_display()
        self.assertEqual(prep_categories, OrderedDict([
            (category_varieties, OrderedDict([
                (self.attribute_varieties, OrderedDict([
                    (self.template_margaux.product_variant_id, self.attribute_line_varieties.value_ids)
                ]))
            ])),
            (category_vintage, OrderedDict([
                (self.attribute_vintage, OrderedDict([
                    (self.template_margaux.product_variant_id, self.attribute_line_vintage.value_ids)
                ]))
            ])),
        ]))
