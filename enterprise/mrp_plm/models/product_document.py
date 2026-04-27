# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = 'product.document'

    def _default_attached_on_mrp(self):
        return "bom" if self.env.context.get('eco_bom') else super()._default_attached_on_mrp()

    origin_attachment_id = fields.Many2one('ir.attachment')
    origin_res_model = fields.Char("Origin Model", related="origin_attachment_id.res_model")
    origin_res_name = fields.Char("Origin Name", related="origin_attachment_id.res_name")
