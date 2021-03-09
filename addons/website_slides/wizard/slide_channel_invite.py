# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import formataddr

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SlideChannelInvite(models.TransientModel):
    _name = 'slide.channel.invite'
    _description = 'Channel Invitation Wizard'

    # composer content
    subject = fields.Char('Subject', compute='_compute_subject', readonly=False, store=True)
    body = fields.Html('Contents', sanitize_style=True, compute='_compute_body', readonly=False, store=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    template_id = fields.Many2one(
        'mail.template', 'Use template',
        domain="[('model', '=', 'slide.channel.partner')]")
    # recipients
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    # slide channel
    channel_id = fields.Many2one('slide.channel', string='Slide channel', required=True)

    @api.depends('template_id')
    def _compute_subject(self):
        for invite in self:
            if invite.template_id:
                invite.subject = invite.template_id.subject
            elif not invite.subject:
                invite.subject = False

    @api.depends('template_id')
    def _compute_body(self):
        for invite in self:
            if invite.template_id:
                invite.body = invite.template_id.body_html
            elif not invite.body:
                invite.body = False

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        if self.partner_ids:
            signup_allowed = self.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'
            if not signup_allowed:
                invalid_partners = self.env['res.partner'].search([
                    ('user_ids', '=', False),
                    ('id', 'in', self.partner_ids.ids)
                ])
                if invalid_partners:
                    raise UserError(_(
                        'The following recipients have no user account: %s. You should create user accounts for them or allow external sign up in configuration.',
                        ', '.join(invalid_partners.mapped('name'))
                    ))

    @api.model
    def create(self, values):
        if values.get('template_id') and not (values.get('body') or values.get('subject')):
            template = self.env['mail.template'].browse(values['template_id'])
            if not values.get('subject'):
                values['subject'] = template.subject
            if not values.get('body'):
                values['body'] = template.body_html
        return super(SlideChannelInvite, self).create(values)

    def action_invite(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        self.ensure_one()

        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))

        mail_values = []
        for partner_id in self.partner_ids:
            slide_channel_partner = self.channel_id._action_add_members(partner_id)
            if slide_channel_partner:
                mail_values.append(self._prepare_mail_values(slide_channel_partner))

        # TODO awa: change me to create multi when mail.mail supports it
        for mail_value in mail_values:
            self.env['mail.mail'].sudo().create(mail_value)

        return {'type': 'ir.actions.act_window_close'}

    def _prepare_mail_values(self, slide_channel_partner):
        """ Create mail specific for recipient """
        subject = self.env['mail.render.mixin']._render_template(self.subject, 'slide.channel.partner', slide_channel_partner.ids, post_process=True)[slide_channel_partner.id]
        body = self.env['mail.render.mixin']._render_template(self.body, 'slide.channel.partner', slide_channel_partner.ids, post_process=True)[slide_channel_partner.id]
        # post the message
        mail_values = {
            'email_from': self.env.user.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'model': None,
            'res_id': None,
            'subject': subject,
            'body_html': body,
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'auto_delete': True,
            'recipient_ids': [(4, slide_channel_partner.partner_id.id)]
        }

        # optional support of notif_layout in context
        notif_layout = self.env.context.get('notif_layout', self.env.context.get('custom_layout'))
        if notif_layout:
            try:
                template = self.env.ref(notif_layout, raise_if_not_found=True)
            except ValueError:
                _logger.warning('QWeb template %s not found when sending slide channel mails. Sending without layouting.' % (notif_layout))
            else:
                # could be great to use _notify_prepare_template_context someday
                template_ctx = {
                    'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=self.channel_id.name)),
                    'model_description': self.env['ir.model']._get('slide.channel').display_name,
                    'record': slide_channel_partner,
                    'company': self.env.company,
                    'signature': self.channel_id.user_id.signature,
                }
                body = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)

        return mail_values
