# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    @api.model
    def _selection_template_model(self):
        return super(EventTypeMail, self)._selection_template_model() + [('social.post.template', 'Social')]

    notification_type = fields.Selection(selection_add=[('social_post', 'Social Post')], ondelete={'social_post': 'set default'})

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        social_model = self.env['ir.model']._get('social.post.template')
        social_mails = self.filtered(lambda mail: mail.notification_type == 'social_post')
        social_mails.template_model_id = social_model
        super(EventTypeMail, self - social_mails)._compute_template_model_id()

    @api.constrains('template_ref', 'interval_type')
    def _check_interval_type(self):
        """Cannot select "after_sub" if the notification type is "social_post"."""
        for mail in self:
            if mail.template_ref and mail.template_ref._name == 'social.post.template' and mail.interval_type == 'after_sub':
                raise UserError(_('As social posts have no recipients, they cannot be triggered by registrations.'))
