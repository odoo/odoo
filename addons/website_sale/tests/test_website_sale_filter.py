# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.tests.common import HttpCase, TransactionCase
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.osv import expression


class TestUi(HttpCase, TransactionCase):

    def setUp(self):
        super(TestUi, self).setUp()

        self.website = self.env['website'].browse(1)
        self.WebsiteSaleController = WebsiteSale()

        Category = self.env['product.public.category']
        Product = self.env['product.template']

        Category.search([]).unlink()  # remove demo data to ease testing

        category_1 = Category.create({'name': "category_1"})
        category_1_1 = Category.create({'name': "category_1_1", 'parent_id': category_1.id})
        category_1_1_1 = Category.create({'name': "category_1_1_1", 'parent_id': category_1_1.id})
        category_1_2 = Category.create({'name': "category_1_2", 'parent_id': category_1.id})
        category_1_2_1 = Category.create({'name': "category_1_2_1", 'parent_id': category_1_2.id})

        category_2 = Category.create({'name': "category_2"})
        Category.create({'name': "category_2_1", 'parent_id': category_2.id})  # unused child category
        category_2_2 = Category.create({'name': "category_2_2", 'parent_id': category_2.id})  # unused child category

        category_3 = Category.create({'name': "category_3"})  # category without product
        category_3_1 = Category.create({'name': "category_3_1", 'parent_id': category_3.id})  # Only the sub_category has product

        category_4 = Category.create({'name': "category_4"})  # category without child

        Category.create({'name': "category_5"})  # unused main category

        Product.create({'name': "product_a", 'website_published': True, 'public_categ_ids': category_1})
        Product.create({'name': "product_b", 'website_published': True, 'public_categ_ids': category_1})
        Product.create({'name': "product_c_1", 'website_published': True, 'public_categ_ids': category_1})
        Product.create({'name': "product_d_1", 'website_published': True, 'public_categ_ids': category_1_1})
        Product.create({'name': "product_d_2", 'website_published': True, 'public_categ_ids': category_1_1_1})
        Product.create({'name': "product_e", 'website_published': True, 'public_categ_ids': category_1_2})
        Product.create({'name': "product_f", 'website_published': True, 'public_categ_ids': category_1_2_1})

        Product.create({'name': "product_c_2", 'website_published': True, 'public_categ_ids': category_2})
        Product.create({'name': "product_d_3", 'website_published': True, 'public_categ_ids': category_2_2})

        Product.create({'name': "product_d_4", 'website_published': True, 'public_categ_ids': category_3_1})

        Product.create({'name': "product_h", 'website_published': True, 'public_categ_ids': category_4})

    def test_01_category_filtering(self):
        self.start_tour("/shop", 'website_sale_category_filter', login='admin')
