# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.api import Environment
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class TestWebsiteSequence(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env.ref('website.default_website')
        cls.public_user = cls.env.ref('base.public_user')

        ProductTemplate = cls.env['product.template']
        product_templates = ProductTemplate.search([])
        # if stock is installed we can't archive since there is orderpoints
        if 'orderpoint_ids' in cls.env['product.product']:
            product_templates.product_variant_ids.orderpoint_ids.write({'active': False})
        # if pos loyalty is installed we can't archive since there are loyalty rules and rewards
        if 'loyalty.program' in cls.env:
            programs = cls.env['loyalty.program'].search([])
            programs.active = False
            programs.coupon_ids.unlink()
            programs.unlink()
        product_templates.write({'active': False})
        cls.product_tmpls = cls.p1, cls.p2, cls.p3, cls.p4 = ProductTemplate.create([{
            'name': 'First Product',
            'website_sequence': 100,
        }, {
            'name': 'Second Product',
            'website_sequence': 180,
        }, {
            'name': 'Third Product',
            'website_sequence': 225,
        }, {
            'name': 'Last Product',
            'website_sequence': 250,
        }])

    def get_product_sort_mapping(self, label):
        context = dict(self.env.context, website_id=self.website.id, lang='en_US')
        env = Environment(self.env.cr, self.public_user.id, context)
        with MockRequest(env, website=self.website.with_env(env)) as req:
            product_sort_mapping = req.env['website']._get_product_sort_mapping()
            return next(k for k, v in product_sort_mapping if v == label)

    def get_sorted_products(self, order, products=None):
        products = products or self.product_tmpls
        return products.search(
            [('id', 'in', products.ids)],
            order=order,
        )

    def assertProductOrdering(self, products, order):
        """Assert `products` are sorted by `order`.

        :param records products: The products or product templates to check.
        :param str order: Expect ordering, in the same format as used by `search`.
        """
        expected = self.get_sorted_products(order, products=products)
        self.assertSequenceEqual(products, expected, f"Products should be ordered on '{order}'")

    def test_01_website_sequence(self):
        sequence_order = self.get_product_sort_mapping("Featured")
        self.assertProductOrdering(self.p1 + self.p2 + self.p3 + self.p4, sequence_order)
        # 100:1, 180:2, 225:3, 250:4
        self.p2.set_sequence_down()
        # 100:1, 180:3, 225:2, 250:4
        self.assertProductOrdering(self.p1 + self.p3 + self.p2 + self.p4, sequence_order)
        self.p4.set_sequence_up()
        # 100:1, 180:3, 225:4, 250:2
        self.assertProductOrdering(self.p1 + self.p3 + self.p4 + self.p2, sequence_order)
        self.p2.set_sequence_top()
        # 95:2, 100:1, 180:3, 225:4
        self.assertProductOrdering(self.p2 + self.p1 + self.p3 + self.p4, sequence_order)
        self.p1.set_sequence_bottom()
        # 95:2, 180:3, 225:4, 230:1
        self.assertProductOrdering(self.p2 + self.p3 + self.p4 + self.p1, sequence_order)

        current_products = self.get_sorted_products(sequence_order)
        current_sequences = current_products.mapped('website_sequence')
        self.assertEqual(current_sequences, [95, 180, 225, 230], "Wrong sequence order (2)")

        self.p2.website_sequence = 1
        self.p3.set_sequence_top()
        # -4:3, 1:2, 225:4, 230:1
        self.assertEqual(self.p3.website_sequence, -4, "`website_sequence` should go below 0")

        new_product = self.env['product.template'].create({
            'name': 'Last Newly Created Product',
        })
        current_products += new_product

        self.assertEqual(
            self.get_sorted_products(sequence_order, current_products)[-1],
            new_product,
            "New product should be last",
        )

    def test_02_newest_arrivals(self):
        def toggle_publish(products, delta=timedelta(seconds=5)):
            publish_date = datetime.now()
            for product in products:
                publish_date += delta
                with freeze_time(publish_date):
                    product.website_publish_button()
                    product.flush_recordset()  # force computations

        newest_arrival_order = self.get_product_sort_mapping("Newest Arrivals")

        toggle_publish(self.product_tmpls)
        # Products were published sequentially,
        # so first product is "oldest" arrival & last product is "newest" arrival
        target = self.product_tmpls[::-1]
        self.assertTrue(all(self.product_tmpls.mapped('is_published')))
        self.assertProductOrdering(target, newest_arrival_order)

        publish_dates = self.product_tmpls.mapped('publish_date')
        toggle_publish(self.product_tmpls)
        self.assertFalse(any(self.product_tmpls.mapped('is_published')))
        self.assertSequenceEqual(
            self.product_tmpls.mapped('publish_date'),
            publish_dates,
            "Unpublishing should not affect publishing date",
        )

        toggle_publish(self.p2, delta=timedelta(days=1))
        self.assertEqual(
            self.get_sorted_products(newest_arrival_order)[0],
            self.p2,
            "Most recently published product should appear first",
        )
