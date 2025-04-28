# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools import is_html_empty
from odoo.tools.translate import html_translate


class ProductTag(models.Model):
    _name = 'product.tag'
    _inherit = ['product.tag', 'pos.load.mixin']

    pos_description = fields.Html(string='Description', translate=html_translate)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'pos_description']

    def write(self, vals):
        if vals.get('pos_description') and is_html_empty(vals['pos_description']):
            vals['pos_description'] = ''
        return super().write(vals)
