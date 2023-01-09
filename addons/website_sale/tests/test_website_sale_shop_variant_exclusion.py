# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestShopVariantExclusion(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    @classmethod
    def setUpClass(cls):
        super(TestShopVariantExclusion, cls).setUpClass()
        # create a template
        cls.product_template = cls.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'list_price': 750,
        })

        cls.first_product_attribute = cls.env['product.attribute'].create({
            'name': 'First Attribute',
            'visibility': 'visible',
            'sequence': 10,
        })

        cls.second_product_attribute = cls.env['product.attribute'].create({
            'name': 'Second Attribute',
            'visibility': 'visible',
        })

        cls.product_attribute_value_1 = cls.env['product.attribute.value'].create({
            'name': 'First Attribute - Value 1',
            'attribute_id': cls.first_product_attribute.id,
            'sequence': 1,
        })
        cls.product_attribute_value_2 = cls.env['product.attribute.value'].create({
            'name': 'First Attribute - Value 2',
            'attribute_id': cls.first_product_attribute.id,
        })
        cls.product_attribute_value_3 = cls.env['product.attribute.value'].create({
            'name': 'Second Attribute - Value 1',
            'attribute_id': cls.second_product_attribute.id,
        })
        cls.product_attribute_value_4 = cls.env['product.attribute.value'].create({
            'name': 'Second Attribute - Value 2',
            'attribute_id': cls.second_product_attribute.id,
        })

        # set attribute and attribute values on the template
        cls.env['product.template.attribute.line'].create([{
            'attribute_id': cls.first_product_attribute.id,
            'product_tmpl_id': cls.product_template.id,
            'value_ids': [(6, 0, [cls.product_attribute_value_1.id, cls.product_attribute_value_2.id])]
        }])

        cls.env['product.template.attribute.line'].create([{
            'attribute_id': cls.second_product_attribute.id,
            'product_tmpl_id': cls.product_template.id,
            'value_ids': [(6, 0, [cls.product_attribute_value_3.id, cls.product_attribute_value_4.id])]
        }])

    def _add_exclude(self, ptav1, ptav2, product_template):
        ptav1.update({
            'exclude_for': [(0, 0, {
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, [ptav2.id])]
            })]
        })

    def _get_product_template_attribute_value(self, product_attribute_value, model):
        """
            Return the `product.template.attribute.value` matching
                `product_attribute_value` for self.

            :param: recordset of one product.attribute.value
            :return: recordset of one product.template.attribute.value if found
                else empty
        """
        return model.valid_product_template_attribute_line_ids.filtered(
            lambda l: l.attribute_id == product_attribute_value.attribute_id
        ).product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == product_attribute_value
        )

    def test_admin_shop_variant_exclusion(self):
        # Enable Variant Group
        self.env.ref('product.group_product_variant').write({'users': [(4, self.env.ref('base.user_admin').id)]})
        ptav1 = self._get_product_template_attribute_value(self.product_attribute_value_1, self.product_template)
        ptav2 = self._get_product_template_attribute_value(self.product_attribute_value_3, self.product_template)
        self._add_exclude(ptav1, ptav2, self.product_template)
        # Enable Product Attributes Left Panel
        self.env['ir.ui.view'].with_context(active_test=False).search(
            [('key', '=', 'website_sale.products_attributes')]).write({'active': True})
        self.start_tour("/", 'shop_variant_exclusion', login="admin")
