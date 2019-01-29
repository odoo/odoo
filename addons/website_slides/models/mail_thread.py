# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super(MailThread, self).message_post(**kwargs)
        if self._name == 'slide.channel':
            rating_value = kwargs.get('rating_value', False)
            author_id = int(kwargs.get('author_id', 0))
            if rating_value and author_id:
                # apply karma gain rule only once
                self.env['res.users'].search([('partner_id', '=', author_id)]).add_karma(self.karma_gen_channel_rank)
        return message
