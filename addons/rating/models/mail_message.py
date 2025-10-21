# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    rating_ids = fields.One2many("rating.rating", "message_id", string="Related ratings")
    rating_id = fields.Many2one("rating.rating", compute="_compute_rating_id")
    rating_value = fields.Float(
        'Rating Value', compute='_compute_rating_value', compute_sudo=True,
        store=False, search='_search_rating_value')

    @api.depends("rating_ids.consumed")
    def _compute_rating_id(self):
        for message in self:
            message.rating_id = message.rating_ids.filtered(lambda rating: rating.consumed).sorted(
                "create_date", reverse=True
            )[:1]

    @api.depends('rating_ids', 'rating_ids.rating')
    def _compute_rating_value(self):
        for message in self:
            message.rating_value = message.rating_id.rating if message.rating_id else 0.0

    def _search_rating_value(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        ratings = self.env['rating.rating'].sudo()._search([
            ('rating', operator, operand),
            ('message_id', '!=', False),
            ('consumed', '=', True),
        ])
        return [('id', 'in', ratings.subselect('message_id'))]

    def _to_store_defaults(self, target):
        # sudo: mail.message - guest and portal user can receive rating of accessible message
        return super()._to_store_defaults(target) + [Store.One("rating_id", sudo=True)]

    def _is_empty(self):
        return super()._is_empty() and not self.rating_id
