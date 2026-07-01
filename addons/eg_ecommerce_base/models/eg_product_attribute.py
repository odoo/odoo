from odoo import models, fields, api


class EgProductAttribute(models.Model):
    _name = "eg.product.attribute"

    odoo_attribute_id = fields.Many2one(comodel_name="product.attribute", string="Odoo Attribute", required=True)
    name = fields.Char(related="odoo_attribute_id.name", string="Name", store=True, readonly=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    inst_attribute_id = fields.Char(string="Instance Attribute")
    update_required = fields.Boolean(string="Update Required")
    eg_value_ids = fields.One2many(comodel_name="eg.attribute.value", inverse_name="inst_attribute_id", string="Values")
    _sql_constraints = [
        ('inst_attribute_uniq', 'unique(instance_id, inst_attribute_id)',
         'Combination of instance and inst_attribute_id must be unique!!!'),
    ]
