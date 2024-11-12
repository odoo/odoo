# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class RatingRating(models.Model):
    _inherit = "rating.rating"

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for rating in self:
            # cannot change the rec_name of session since it is use to create the bus channel
            # so, need to override this method to set the same alternative rec_name as in reporting
            if rating.res_model == 'discuss.channel':
                current_object = self.env[rating.res_model].sudo().browse(rating.res_id)
                rating.res_name = ('%s / %s') % (current_object.livechat_channel_id.name, current_object.id)
            else:
                super(RatingRating, rating)._compute_res_name()

    def action_open_rated_object(self):
        action = super().action_open_rated_object()
        if self.res_model == 'discuss.channel':
            if self.env[self.res_model].browse(self.res_id):
                ctx = self.env.context.copy()
                ctx.update({'active_id': self.res_id})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'mail.action_discuss',
                    'context': ctx,
                }
            view_id = self.env.ref('im_livechat.discuss_channel_view_form').id
            action['views'] = [[view_id, 'form']]
        return action
