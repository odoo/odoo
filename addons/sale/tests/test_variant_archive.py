# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tools import mute_logger
from odoo.tests.common import SavepointCase


class TestArchiveVariant(SavepointCase):
    at_install = False
    post_install = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.setUpClassTemplate()
        cls.setUpClassAttribute()
        cls.setUpClassProduct()
        cls.partner = cls.env["res.partner"].create({"name": "Partner"})

    @classmethod
    def setUpClassTemplate(cls):
        cls.template_model = cls.env["product.template"]
        cls.pen = cls.template_model.create({"name": "pen"})
        cls.car = cls.template_model.create({"name": "car"})

    @classmethod
    def setUpClassAttribute(cls):
        cls.attribute_model = cls.env["product.attribute"]
        cls.value_model = cls.env["product.attribute.value"]
        cls.attribute_line_model = cls.env["product.template.attribute.line"]
        cls.attribute_value_model = cls.env["product.template.attribute.value"]
        cls.attribute = cls.attribute_model.create({"name": "color"})
        cls.values = cls.env["product.attribute.value"]
        for color in ["red", "blue"]:
            value = cls.value_model.create(
                {"attribute_id": cls.attribute.id, "name": color}
            )
            setattr(cls, color, value)
            cls.values |= value

    @classmethod
    def setUpClassProduct(cls):
        cls.product_model = cls.env["product.product"]
        cls.pen_attribute_line = cls.attribute_line_model.create(
            {
                "product_tmpl_id": cls.pen.id,
                "attribute_id": cls.attribute.id,
                "value_ids": [(6, 0, cls.values.ids)],
            }
        )
        cls.car_attribute_line = cls.attribute_line_model.create(
            {
                "product_tmpl_id": cls.car.id,
                "attribute_id": cls.attribute.id,
                "value_ids": [(6, 0, cls.values.ids)],
            }
        )
        cls.attribute_lines = cls.pen_attribute_line | cls.car_attribute_line

    @classmethod
    def _create_sale_order(cls, products):
        """Create a sale order with given products."""
        sale_form = Form(cls.env["sale.order"])
        sale_form.partner_id = cls.partner
        with mute_logger("odoo.tests.common.onchange"):
            for product in products:
                with sale_form.order_line.new() as line:
                    line.product_id = product
                    line.product_uom_qty = 1
        return sale_form.save()

    def _get_template_value(self, value, attribute_line=None):
        domain = [("product_attribute_value_id", "=", value.id)]
        if attribute_line is not None:
            domain.append(("attribute_line_id", "=", attribute_line.id))
        return self.attribute_value_model.search(domain)

    def test_value_unlink(self):
        # No SO has been created, therefore we should be able to unlink values.
        remaining_values = self.values - self.red
        # Remove red from the attribute lines
        self.attribute_lines.write(
            {"value_ids": [(6, 0, remaining_values.ids)]}
        )
        # then unlink it
        self.red.unlink()
        updated_values = self.attribute.value_ids
        self.assertEqual(len(updated_values), 1)
        self.assertNotIn(self.red, updated_values)

    def test_value_archive(self):
        # If a value is only referenced by archived variants, then
        # the value should be archived instead.
        template_values = self._get_template_value(self.red)
        products = template_values.ptav_product_variant_ids
        # There should be red car and red pen in the recordset
        self.assertEqual(len(products), 2)
        self._create_sale_order(products)
        # Trying to unlink the value here should raise an exception
        # since it's still referenced by the car and pen product templates
        regex = f"You cannot delete the value color: red"
        with self.assertRaisesRegex(UserError, regex):
            self.red.unlink()
        # Remove the value from the set
        self.attribute_lines.write({"value_ids": [(3, self.red.id, 0)]})
        # The variants should be archived instead of unlinked,
        # since they are referenced by a sale.order.line
        self.assertFalse(any(products.mapped("active")))
        # now, since the the variant is archived, we shouldn't be able
        self.red.unlink()
        self.assertFalse(self.red.active)

    def test_value_non_archiveable(self):
        # Even if one variant is archived, it should be possible to
        # archive or unlink an attribute value, as long there is an
        # active variant.
        pen_template_value = self._get_template_value(
            self.red, self.pen_attribute_line
        )
        red_pen = pen_template_value.ptav_product_variant_ids
        self.assertEqual(len(red_pen), 1)
        self._create_sale_order(red_pen)
        # Remove the value from the set
        self.pen_attribute_line.value_ids = [(3, self.red.id, 0)]
        # The variant should be archived instead of unlinked,
        # since it's referenced by a sale.order.line
        self.assertFalse(red_pen.active)
        # The red car variant is still active, so we shouldn't be able
        # to archive or unlink the value, and odoo should raise
        # an exception saying that red is still referenced by car
        regex = r"You cannot delete the value color: red.*car"
        with self.assertRaisesRegex(UserError, regex):
            self.red.unlink()
