# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailGatewayMessage(models.Model):
    _name = 'mail.gateway.message'
    _description = 'Custom Message Gateway'

    subject = fields.Char()
    body = fields.Html()
    email_from = fields.Char()
    message_id = fields.Char()
    parent_id = fields.Many2one('mail.gateway.message')
    mail_gateway_id = fields.Many2one('mail.gateway.custom')


class MailGateway(models.Model):
    _name = 'mail.gateway.custom'
    _description = 'Custom Mail Gateway'

    name = fields.Char()
    custom_message_ids = fields.One2many('mail.gateway.message', 'mail_gateway_id')

    def _message_route_process_prepare_post(self, subtype_id, **post_params):
        parent_id = post_params.pop('parent_id', False)
        post_params['is_internal'] = False

        subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')
        post_params = super(MailGateway, self)._message_route_process_prepare_post(subtype_id, **post_params)

        post_params['parent_id'] = parent_id
        return post_params

    def message_post(self, **kwargs):
        self.ensure_one()
        new_msg = self.env['mail.gateway.message'].create({
            'subject': kwargs.get('subject'),
            'body': kwargs.get('body'),
            'mail_gateway_id': self.id,
        })
        return False

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        return self.create(custom_values or {})

    def message_update(self, msg_dict, update_vals=None):
        if update_vals:
            self.write(update_vals)
        return True

    def _creation_subtype(self):
        return self.env['mail.message.subtype']
