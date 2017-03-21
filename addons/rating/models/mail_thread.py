# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification', subtype=None, parent_id=False, attachments=None, content_subtype='html', **kwargs):
        rating_value = kwargs.get('rating_value')
        message = super(MailThread, self).message_post(body=body, subject=subject, message_type=message_type, subtype=subtype, parent_id=parent_id, attachments=attachments, content_subtype=content_subtype, **kwargs)
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
