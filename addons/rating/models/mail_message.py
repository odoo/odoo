# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    rating_ids = fields.One2many('rating.rating', 'message_id', groups='base.group_user', string='Related ratings')
    rating_value = fields.Float(
        'Rating Value', compute='_compute_rating_value', compute_sudo=True,
        store=False, search='_search_rating_value')

    @api.depends('rating_ids', 'rating_ids.rating')
    def _compute_rating_value(self):
        ratings = self.env['rating.rating'].search([('message_id', 'in', self.ids), ('consumed', '=', True)], order='create_date DESC')
        mapping = dict((r.message_id.id, r.rating) for r in ratings)
        for message in self:
            message.rating_value = mapping.get(message.id, 0.0)

    def _search_rating_value(self, operator, operand):
        ratings = self.env['rating.rating'].sudo().search([
            ('rating', operator, operand),
            ('message_id', '!=', False)
        ])
        return [('id', 'in', ratings.mapped('message_id').ids)]

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        rating_mixin_messages = self.filtered(lambda message:
            message.model
            and message.res_id
            and issubclass(self.pool[message.model], self.pool['rating.mixin'])
        )
        if rating_mixin_messages:
            ratings = self.env['rating.rating'].sudo().search([('message_id', 'in', rating_mixin_messages.ids), ('consumed', '=', True)])
            for rating in ratings:
                store.add(
                    "Message",
                    {
                        "id": rating.message_id.id,
                        "rating": {
                            "id": rating.id,
                            "ratingImageUrl": rating.rating_image_url,
                            "ratingText": rating.rating_text,
                        },
                    },
                )
