# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools import is_html_empty
from odoo.tools.translate import adapt_translated_field_value


class ProductTag(models.Model):
    _name = 'product.tag'
    _inherit = ['product.tag', 'pos.load.mixin']

    pos_description = fields.Html(string='Description', translate=True)
    has_image = fields.Boolean(compute='_compute_has_image')

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'pos_description', 'color', 'has_image', 'write_date']

    @api.depends('has_image')
    def _compute_has_image(self):
        for record in self:
            record.has_image = bool(record.image)

    def write(self, vals):
        if vals.get('pos_description'):
            vals['pos_description'] = adapt_translated_field_value(
                self.env, vals['pos_description'],
                lambda lang, v: '' if is_html_empty(v) else v
            )
        return super().write(vals)
