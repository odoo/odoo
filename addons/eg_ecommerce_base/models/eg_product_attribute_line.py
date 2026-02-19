from odoo import models, fields, api


class EgProductAttributeLine(models.Model):
    _name = "eg.product.attribute.line"

    eg_product_attribute_id = fields.Many2one(comodel_name="eg.product.attribute", string="Attribute")
    eg_product_tmpl_id = fields.Many2one(comodel_name="eg.product.template", string="Product Template",
                                         ondelete='cascade')
    eg_value_ids = fields.Many2many(comodel_name="eg.attribute.value", string="Attribute Values")
