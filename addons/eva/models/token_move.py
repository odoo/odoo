from odoo import fields, models


class EvaTokenMove(models.Model):
    _name = 'eva.token.move'
    _description = 'EVA Token Move'

    player_id = fields.Many2one('eva.player', required=True)
    amount = fields.Integer(required=True)
    date = fields.Date(required=True, default=fields.Date.today)
    move_type = fields.Selection([
        ('subscription', 'Subscription'),
        ('game', 'Game'),
        ('manual', 'Manual'),
    ], required=True)
    game_id = fields.Many2one('eva.game')
