# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        rating_id = kwargs.pop('rating_id', False)
        rating_value = kwargs.pop('rating_value', False)
        rating_feedback = kwargs.pop('rating_feedback', False)
        message = super(MailThread, self).message_post(**kwargs)

        # create rating.rating record linked to given rating_value. Using sudo as portal users may have
        # rights to create messages and therefore ratings (security should be checked beforehand)
        if rating_value:
            self.env['rating.rating'].sudo().create({
                'rating': float(rating_value) if rating_value is not None else False,
                'feedback': rating_feedback,
                'res_model_id': self.env['ir.model']._get_id(self._name),
                'res_id': self.id,
                'message_id': message.id,
                'consumed': True,
                'partner_id': self.env.user.partner_id.id,
            })
        elif rating_id:
            self.env['rating.rating'].browse(rating_id).write({'message_id': message.id})

        return message

    def _message_create(self, values_list):
        """ Force usage of rating-specific methods and API allowing to delegate
        computation to records. Keep methods optimized and skip rating_ids
        support to simplify MailThrad main API. """
        if not isinstance(values_list, (list)):
            values_list = [values_list]
        if any(values.get('rating_ids') for values in values_list):
            raise ValueError(_("Posting a rating should be done using message post API."))
        return super()._message_create(values_list)
