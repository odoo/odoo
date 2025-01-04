from odoo import api, fields, models


class CardDimension(models.Model):
    _name = "card.dimension"
    _description = 'Card Dimension'
    _order = 'ratio'

    name = fields.Char(required=True)

    width = fields.Integer(string="Width", required=True)
    height = fields.Integer(string="Height", required=True)
    ratio = fields.Float(string="Ratio", compute='_compute_ratio', store=True)

    @api.depends('height', 'width')
    def _compute_ratio(self):
        for record in self:
            record.ratio = round(record.width / record.height, 2) if record.width and record.height else 1
