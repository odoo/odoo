# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SlideChannelInvite(models.TransientModel):
    _name = 'slide.channel.invite'
    _inherit = ['mail.composer.mixin']
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

    def _compute_subject(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it. When removing the
        template, reset it. """
        for composer_mixin in self:
            if composer_mixin.template_id.subject:
                if composer_mixin.channel_id.channel_partner_all_ids:
                    rec = composer_mixin.channel_id.channel_partner_all_ids[0]
                else:
                    rec = self.env[composer_mixin.render_model].new({
                        'channel_id': composer_mixin.channel_id.id,
                        'partner_id': composer_mixin.channel_id.create_uid.partner_id.id,
                    })
                composer_mixin.subject = composer_mixin.template_id._render_field(
                    'subject',
                    [rec.id],
                    compute_lang=True,
                    options={'post_process': True},
                )[rec.id]
            elif not composer_mixin.template_id:
                composer_mixin.subject = False
            # elif composer_mixin.template_id.subject:
            #     composer_mixin.subject = composer_mixin.template_id.subject

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

        self.composer_send_mail(
            attendees_to_reinvite | channel_partners,
            attachment_ids=self.attachment_ids.ids,
            compute_lang=True,
        )

        return {'type': 'ir.actions.act_window_close'}

    def _get_recipient_data(self, record):
        data = super()._get_recipient_data(record)
        template_ctx = {
            "record_name": self.channel_id.name,
            "show_button": True,
            "button_access": {
                "url": record.invitation_link,
                "title": _("Getting Started"),
            },
            "subtitles": [],
            "signature": Markup("<div>-- <br/>%s</div>")
            % self.channel_id.user_id.signature
            if not is_html_empty(self.channel_id.user_id.signature)
            else False,
        }
        data["template_context"].update(template_ctx)
        data["mail_values"].update({"recipient_ids": [(4, record.partner_id.id)]})
        return data
