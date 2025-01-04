from odoo import fields, models


class CardTemplate(models.Model):
    _name = 'card.template'
    _description = 'Marketing Card Template'

    name = fields.Char(required=True, translate=True)
    default_background = fields.Image()
    body = fields.Html(sanitize_tags=False, sanitize_attributes=False)

    primary_color = fields.Char(default='#f9f9f9', required=True)
    secondary_color = fields.Char(default='#000000', required=True)
    primary_text_color = fields.Char(default='#000000', required=True)
    secondary_text_color = fields.Char(default='#ffffff', required=True)

    card_dimension_id = fields.Many2one('card.dimension', ondelete='restrict')
