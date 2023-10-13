# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SlideChannelInvite(models.TransientModel):
    _name = 'slide.channel.invite'
    _inherit = 'mail.composer.mixin'
    _description = 'Channel Invitation Wizard'

    # composer content
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    send_email = fields.Boolean('Send Email', compute="_compute_send_email", readonly=False, store=True)
    # recipients
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    # slide channel
    channel_id = fields.Many2one('slide.channel', string='Course', required=True)
    channel_invite_url = fields.Char('Course Link', compute='_compute_channel_invite_url')
    channel_visibility = fields.Selection(related='channel_id.visibility')
    channel_published = fields.Boolean(related='channel_id.is_published')
    # membership
    enroll_mode = fields.Boolean(
        'Enroll partners', readonly=True,
        help='Whether invited partners will be added as enrolled. Otherwise, they will be added as invited.')

    @api.depends('channel_id')
    def _compute_channel_invite_url(self):
        for invite in self:
            channel = invite.channel_id
            invite.channel_invite_url = f'{channel.get_base_url()}/slides/{channel.id}'

    # Overrides of mail.composer.mixin
    @api.depends('channel_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'slide.channel.partner'

    @api.depends('channel_id', 'enroll_mode')
    def _compute_send_email(self):
        self.send_email = self.channel_visibility != 'public' or self.enroll_mode

    def action_invite(self):
        """ Process the wizard content and proceed with sending the related email(s),
            rendering any template patterns on the fly if needed. This method is used both
            to add members as 'joined' (when adding attendees) and as 'invited' (on invitation),
            depending on the value of enroll_mode. Archived members can be invited or enrolled.
            They will become 'invited', or another status if enrolled depending on their progress.
            Invited members can be reinvited, or enrolled depending on enroll_mode. """
        self.ensure_one()

        if not self.send_email:
            return
        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        if not self.partner_ids:
            raise UserError(_("Please select at least one recipient."))

        mail_values = []
        attendees_to_reinvite = self.env['slide.channel.partner'].search([
            ('member_status', '=', 'invited'),
            ('channel_id', '=', self.channel_id.id),
            ('partner_id', 'in', self.partner_ids.ids)
        ]) if not self.enroll_mode else self.env['slide.channel.partner']

        channel_partners = self.channel_id._action_add_members(
            self.partner_ids - attendees_to_reinvite.partner_id,
            member_status='joined' if self.enroll_mode else 'invited',
            raise_on_access=True
        )
        if not self.enroll_mode:
            (attendees_to_reinvite | channel_partners).last_invitation_date = fields.Datetime.now()

        for channel_partner in (attendees_to_reinvite | channel_partners):
            mail_values.append(self._prepare_mail_values(channel_partner))
        self.env['mail.mail'].sudo().create(mail_values)

        return {'type': 'ir.actions.act_window_close'}

    def _prepare_mail_values(self, slide_channel_partner):
        """ Create mail specific for recipient """
        subject = self._render_field('subject', slide_channel_partner.ids)[slide_channel_partner.id]
        body = self._render_field('body', slide_channel_partner.ids)[slide_channel_partner.id]
        # post the message
        mail_values = {
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'author_id': self.env.user.partner_id.id,
            'auto_delete': self.template_id.auto_delete if self.template_id else True,
            'body_html': body,
            'email_from': self.env.user.email_formatted,
            'model': None,
            'recipient_ids': [(4, slide_channel_partner.partner_id.id)],
            'res_id': None,
            'subject': subject,
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
