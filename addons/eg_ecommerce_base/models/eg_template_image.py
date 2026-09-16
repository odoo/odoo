from odoo import models, fields, api


class EgTemplateImage(models.Model):
    _name = "eg.template.image"

    eg_template_id = fields.Many2one(comodel_name="eg.product.template", string="Product Template", ondelete='cascade')
    template_image = fields.Binary(string="Image")
    name = fields.Char(string="Name")
