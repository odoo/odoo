# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteSaleExtraField(models.Model):
    _name = 'website.sale.extra.field'
    _description = "E-Commerce Extra Info Shown on product page"
    _order = 'sequence'

    website_id = fields.Many2one(comodel_name='website', index='btree_not_null')
    sequence = fields.Integer(default=10)
    field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        domain=[('model_id.model', '=', 'product.template'), ('ttype', 'in', ['char', 'binary'])],
        required=True,
        ondelete='cascade'
    )
    label = fields.Char(related='field_id.field_description')
    name = fields.Char(related='field_id.name')
