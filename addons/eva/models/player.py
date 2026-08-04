from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class EvaPlayer(models.Model):
    _name = 'eva.player'
    _description = 'EVA Player'

    name = fields.Char('Username', required=True)
    player_name = fields.Char(related='user_id.name')
    user_id = fields.Many2one('res.users', required=True)
    game_ids = fields.Many2many('eva.game', 'eva_game_player_rel', string='Games')
    game_count = fields.Integer(compute='_compute_game_count')

    tokens_per_month = fields.Integer(required=True, default=0)
    tokens_grant_day = fields.Integer(required=True, default=1)
    token_move_ids = fields.One2many('eva.token.move', 'player_id')
    token_balance = fields.Integer(compute='_compute_token_balance', inverse='_inverse_token_balance', store=True)
    tokens_reserved = fields.Integer(compute='_compute_tokens_reserved')
    tokens_available = fields.Integer(compute='_compute_tokens_available')

    @api.depends('token_move_ids.amount')
    def _compute_token_balance(self):
        for player in self:
            player.token_balance = sum(player.token_move_ids.mapped('amount'))

    def _inverse_token_balance(self):
        for player in self:
            diff = player.token_balance - sum(player.token_move_ids.mapped('amount'))
            if diff:
                self.env['eva.token.move'].create({
                    'player_id': player.id,
                    'amount': diff,
                    'move_type': 'manual',
                    'date': fields.Date.today(),
                })

    @api.depends('game_ids')
    def _compute_tokens_reserved(self):
        for player in self:
            player.tokens_reserved = len(player.game_ids.filtered(lambda g: g.state == 'draft'))

    @api.depends('token_balance', 'tokens_reserved')
    def _compute_tokens_available(self):
        for player in self:
            player.tokens_available = player.token_balance - player.tokens_reserved

    def _compute_game_count(self):
        for player in self:
            player.game_count = len(player.game_ids)

    def action_open_games(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Games',
            'res_model': 'eva.game',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.game_ids.ids)],
        }

    @api.model
    def _tokens_subscriptions(self):
        today = fields.Date.today()
        players_with_subscription = self.search([('tokens_per_month', '>', 0)])
        last_day_of_month = (today + relativedelta(day=31)).day
        players_to_grant_tokens = players_with_subscription.filtered(
            lambda p: min(p.tokens_grant_day, last_day_of_month) == today.day)

        for player in players_to_grant_tokens:
            self.env['eva.token.move'].create({
                'player_id': player.id,
                'amount': player.tokens_per_month,
                'move_type': 'subscription',
                'date': today,
            })