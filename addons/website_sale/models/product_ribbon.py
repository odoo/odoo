# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _name = 'product.ribbon'
    _description = "Product ribbon"
    _order = 'sequence'

    name = fields.Char(string="Ribbon Name", required=True, translate=True, size=20)
    sequence = fields.Integer(default=10)
    bg_color = fields.Char(string="Background Color", required=True, default='#000000')
    text_color = fields.Char(string="Text Color", required=True, default='#FFFFFF')
    position = fields.Selection(
        string='Position',
        selection=[('left', "Left"), ('right', "Right")],
        required=True,
        default='left',
    )
    style = fields.Selection(
        string="Style",
        selection=[('ribbon', "Ribbon"), ('tag', "Badge")],
        required=True,
        default='ribbon',
    )
    assign = fields.Selection(
        string="Assign",
        selection=[
            ('manual', "Manually"),
            ('sale', "Sale"),
            ('new', "New"),
        ],
        required=True,
        default='manual',
    )
    new_period = fields.Integer(default=30)

    @api.constrains('assign')
    def _check_assign(self):
        for ribbon in self:
            if ribbon.assign != 'manual':
                existing_ribbons = self.search([
                    ('id', '!=', ribbon.id),
                    ('assign', '=', ribbon.assign)
                ], limit=1)
                if existing_ribbons:
                    raise ValidationError(
                        _(
                            "Only one ribbon with the assign %s is allowed.",
                            dict(self._fields['assign'].selection).get(ribbon.assign)
                        )
                    )

    def _get_css_classes(self):
        return f'o_{self.style or "ribbon"} o_{self.position or "left"}'
