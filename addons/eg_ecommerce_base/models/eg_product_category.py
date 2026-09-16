from odoo import models, fields, api


class EgProductCategory(models.Model):
    _name = "eg.product.category"

    odoo_category_id = fields.Many2one(comodel_name="product.category", string="Odoo Category", required=True)
    name = fields.Char(related="odoo_category_id.name", string="Name", store=True, readonly=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    update_required = fields.Boolean(string="Update Required")

    # _sql_constraints = [
    #     ('inst_category_uniq', 'unique(odoo_category_id)',
    #      'Combination of instance and inst_category_id must be unique!!!'),
    # ]

    # add by akash
    parent_id = fields.Char(string="Instance Parent ID")
    real_parent_id = fields.Many2one(comodel_name="eg.product.category", string="Mapping Parent", ondelete='cascade')
    category_image = fields.Binary(string='Image')
    instance_product_category_id = fields.Integer(string="Instance Category ID")
