# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductRibbon(models.Model):
    _name = 'product.ribbon'
    _description = "Product ribbon"

    name = fields.Char(string="Ribbon Name", required=True, translate=True, size=20)
    bg_color = fields.Char(string="Background Color", required=True, default='#000000')
    text_color = fields.Char(string="Text Color", required=True, default='#FFFFFF')
    position = fields.Selection(
        string='Position',
        selection=[('left', "Left"), ('right', "Right")],
        required=True,
        default='left',
    )

    def _get_position_class(self):
        if not self:
            return 'd-none'
        return 'o_ribbon_left' if self.position == 'left' else 'o_ribbon_right'
