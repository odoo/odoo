# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        rating_value = kwargs.pop('rating_value', False)
        message = super(MailThread, self).message_post(**kwargs)
        if rating_value:
            ir_model = self.env['ir.model'].sudo().search([('model', '=', self._name)])
            self.env['rating.rating'].create({
                'rating': float(rating_value) if rating_value is not None else False,
                'res_model_id': ir_model.id,
                'res_id': self.id,
                'message_id': message.id,
                'consumed': True,
                'partner_id': self.env.user.partner_id.id,
            })
        return message
