from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EvaGame(models.Model):
    _name = 'eva.game'
    _description = 'EVA Game Session'
    _order = 'datetime DESC'

    name = fields.Char(required=True)
    datetime = fields.Datetime(required=True, string='Date')
    player_ids = fields.Many2many('eva.player', 'eva_game_player_rel', string='Players')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft', required=True)

    def action_confirm(self):
        for game in self:
            self.env['eva.token.move'].create([{
                'player_id': player.id,
                'amount': -1,
                'move_type': 'game',
                'game_id': game.id,
                'date': fields.Date.today(),
            } for player in game.player_ids])
            game.state = 'confirmed'

    @api.constrains('player_ids')
    def _check_max_players(self):
        for game in self:
            if len(game.player_ids) > 10:
                raise ValidationError("A game cannot have more than 10 players.")

    @api.constrains('player_ids')
    def _check_players_have_token_available(self):
        for game in self:
            if any(token_available <= 0 for token_available in game.player_ids.mapped('tokens_available')):
                raise ValidationError("All players must have tokens available.")