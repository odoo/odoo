from odoo import models, fields, api


class EgAttributeValue(models.Model):
    _name = "eg.attribute.value"

    odoo_attribute_value_id = fields.Many2one(comodel_name="product.attribute.value", string="Odoo Attribute Value",
                                              required=True)
    name = fields.Char(related="odoo_attribute_value_id.name", string="Name", store=True, readonly=True)
    odoo_attribute_id = fields.Many2one(related="odoo_attribute_value_id.attribute_id", string="Attribute",
                                        readonly=True)
    inst_attribute_id = fields.Many2one(comodel_name="eg.product.attribute", string="Instance Attribute", required=True,
                                        ondelete='cascade')
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    # inst_attribute_value_id = fields.Char(string="Instance Attribute Value")
    update_required = fields.Boolean(string="Update Required")

    _sql_constraints = [
        ('inst_attribute_value_uniq', 'unique(instance_id, instance_value_id, inst_attribute_id )',
         'Combination of instance and instance value ID must be unique!!!')]

    # add by akash
    instance_value_id = fields.Integer(string="Instance Value ID")
