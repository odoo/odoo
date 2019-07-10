# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from email.utils import formataddr

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SlideChannelInvite(models.TransientModel):
    _name = 'slide.channel.invite'
    _description = 'Channel Invitation Wizard'

    @api.model
    def _default_email_from(self):
        if self.env.user.email:
            return formataddr((self.env.user.name, self.env.user.email))
        raise UserError(_("Unable to post message, please configure the sender's email address."))

    @api.model
    def _default_author_id(self):
        return self.env.user.partner_id

    # composer content
    subject = fields.Char('Subject')
    body = fields.Html('Contents', default='', sanitize_style=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    template_id = fields.Many2one(
        'mail.template', 'Use template',
        domain="[('model', '=', 'slide.channel.partner')]")
    # origin
    email_from = fields.Char('From', default=_default_email_from)
    author_id = fields.Many2one(
        'res.partner', 'Author',
        ondelete='set null', default=_default_author_id)
    # recipients
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    # slide channel
    channel_id = fields.Many2one('slide.channel', string='Slide channel', required=True)
    channel_url = fields.Char(related="channel_id.website_url", readonly=True)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """ Make the 'subject' and 'body' field match the selected template_id """
        if self.template_id:
            self.subject = self.template_id.subject
            self.body = self.template_id.body_html

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
                    raise UserError(
                        _('The following recipients have no user account: %s. You should create user accounts for them or allow external sign up in configuration.' %
                            (','.join(invalid_partners.mapped('name')))))

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
        subject = self.env['mail.template']._render_template(self.subject, 'slide.channel.partner', slide_channel_partner.id, post_process=True)
        body = self.env['mail.template']._render_template(self.body, 'slide.channel.partner', slide_channel_partner.id, post_process=True)
        # post the message
        mail_values = {
            'email_from': self.email_from,
            'author_id': self.author_id.id,
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
                template_ctx = {
                    'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=self.channel_id.name)),
                    'model_description': self.env['ir.model']._get('website_slides.slide_channel').display_name,
                    'company': self.env.company,
                }
                body = template.render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                mail_values['body_html'] = self.env['mail.thread']._replace_local_links(body)

        return mail_values
