# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestUpdateProductAttributeValueWizard(ProductVariantsCommon):

    def test_add_to_products(self):
        self.assertNotIn(
            self.size_attribute_m,
            self.product_template_shirt.attribute_line_ids.value_ids,
        )

        action = self.size_attribute_m.action_add_to_products()

        with Form(self.env[action['res_model']].with_context(action['context'])) as wizard:
            wizard_record = wizard.save()

        wizard_record.action_confirm()

        self.assertIn(
            self.size_attribute_m,
            self.product_template_shirt.attribute_line_ids.value_ids,
        )

    def test_update_extra_prices(self):
        self.assertEqual(
            self.color_attribute.value_ids.mapped('default_extra_price'),
            self.product_template_sofa.attribute_line_ids.product_template_value_ids.mapped('price_extra'),
        )
        self.assertEqual(
            self.color_attribute.value_ids.mapped('default_extra_price'),
            [0.0, 0.0, 0.0],
        )

        self.color_attribute_red.default_extra_price = 20.0
        self.assertTrue(self.color_attribute_red.default_extra_price_changed)

        wizard = Form.from_action(self.env, self.color_attribute_red.action_update_prices()).save()
        wizard.action_confirm()
        self.assertEqual(
            self.product_template_sofa.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == self.color_attribute_red,
            ).price_extra,
            20.0,
        )
        self.assertFalse(any(self.color_attribute.value_ids.mapped('default_extra_price_changed')))
