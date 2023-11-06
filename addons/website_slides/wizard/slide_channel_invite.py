# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SlideChannelInvite(models.TransientModel):
    _name = 'slide.channel.invite'
    _inherit = 'mail.composer.mixin'
    _description = 'Channel Invitation Wizard'

    # composer content
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    # recipients
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    # slide channel
    channel_id = fields.Many2one('slide.channel', string='Slide channel', required=True)

    # Overrides of mail.composer.mixin
    @api.depends('channel_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'slide.channel.partner'

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

    def action_invite(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        self.ensure_one()

        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        if not self.partner_ids:
            raise UserError(_("Please select at least one recipient."))

        try:
            self.channel_id.check_access_rights('write')
            self.channel_id.check_access_rule('write')
        except AccessError:
            raise AccessError(_('You are not allowed to add members to this course. Please contact the course responsible or an administrator.'))

        mail_values = []
        for partner_id in self.partner_ids:
            slide_channel_partner = self.channel_id._action_add_members(partner_id)
            if slide_channel_partner:
                mail_values.append(self._prepare_mail_values(slide_channel_partner))

        self.env['mail.mail'].sudo().create(mail_values)

        return {'type': 'ir.actions.act_window_close'}

    def _prepare_mail_values(self, slide_channel_partner):
        """ Create mail specific for recipient """
        subject = self._render_field('subject', slide_channel_partner.ids)[slide_channel_partner.id]
        body = self._render_field('body', slide_channel_partner.ids, post_process=True)[slide_channel_partner.id]
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

        # optional support of default_email_layout_xmlid in context
        email_layout_xmlid = self.env.context.get('default_email_layout_xmlid', self.env.context.get('notif_layout'))
        if email_layout_xmlid:
            # could be great to use ``_notify_by_email_prepare_rendering_context`` someday
            template_ctx = {
                'message': self.env['mail.message'].sudo().new({'body': mail_values['body_html'], 'record_name': self.channel_id.name}),
                'model_description': self.env['ir.model']._get('slide.channel').display_name,
                'record': slide_channel_partner,
                'company': self.env.company,
                'signature': self.channel_id.user_id.signature,
            }
            body = self.env['ir.qweb']._render(email_layout_xmlid, template_ctx, engine='ir.qweb', minimal_qcontext=True, raise_if_not_found=False)
            if body:
                mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
            else:
                _logger.warning('QWeb template %s not found when sending slide channel mails. Sending without layout.', email_layout_xmlid)

        return mail_values
