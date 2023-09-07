# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import base64
import logging

from collections import defaultdict
from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Attendee(models.Model):
    """ Calendar Attendee Information """
    _name = 'calendar.attendee'
    _rec_name = 'common_name'
    _description = 'Calendar Attendee Information'
    _order = 'create_date ASC'

    def _default_access_token(self):
        return uuid.uuid4().hex

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    # event
    event_id = fields.Many2one('calendar.event', 'Meeting linked', required=True, ondelete='cascade')
    recurrence_id = fields.Many2one('calendar.recurrence', related='event_id.recurrence_id')
    # attendee
    partner_id = fields.Many2one('res.partner', 'Attendee', required=True, readonly=True)
    email = fields.Char('Email', related='partner_id.email')
    phone = fields.Char('Phone', related='partner_id.phone')
    common_name = fields.Char('Common name', compute='_compute_common_name', store=True)
    access_token = fields.Char('Invitation Token', default=_default_access_token)
    mail_tz = fields.Selection(_tz_get, compute='_compute_mail_tz', help='Timezone used for displaying time in the mail template')
    # state
    state = fields.Selection(STATE_SELECTION, string='Status', readonly=True, default='needsAction')
    availability = fields.Selection(
        [('free', 'Available'), ('busy', 'Busy')], 'Available/Busy', readonly=True)

    @api.depends('partner_id', 'partner_id.name', 'email')
    def _compute_common_name(self):
        for attendee in self:
            attendee.common_name = attendee.partner_id.name or attendee.email

    def _compute_mail_tz(self):
        for attendee in self:
            attendee.mail_tz = attendee.partner_id.tz

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            # by default, if no state is given for the attendee corresponding to the current user
            # that means he's the event organizer so we can set his state to "accepted"
            if 'state' not in values and values.get('partner_id') == self.env.user.partner_id.id:
                values['state'] = 'accepted'
            if not values.get("email") and values.get("common_name"):
                common_nameval = values.get("common_name").split(':')
                email = [x for x in common_nameval if '@' in x]
                values['email'] = email[0] if email else ''
                values['common_name'] = values.get("common_name")
        attendees = super().create(vals_list)
        attendees._subscribe_partner()
        return attendees

    def unlink(self):
        self._unsubscribe_partner()
        return super().unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    def _subscribe_partner(self):
        mapped_followers = defaultdict(lambda: self.env['calendar.event'])
        for event in self.event_id:
            partners = (event.attendee_ids & self).partner_id - event.message_partner_ids
            # current user is automatically added as followers, don't add it twice.
            partners -= self.env.user.partner_id
            mapped_followers[partners] |= event
        for partners, events in mapped_followers.items():
            events.message_subscribe(partner_ids=partners.ids)

    def _unsubscribe_partner(self):
        for event in self.event_id:
            partners = (event.attendee_ids & self).partner_id & event.message_partner_ids
            event.message_unsubscribe(partner_ids=partners.ids)

    def _send_mail_to_attendees(self, mail_template, force_send=False):
        """ Send mail for event invitation to event attendees.
            :param mail_template: a mail.template record
            :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        """
        if isinstance(mail_template, str):
            raise ValueError('Template should be a template record, not an XML ID anymore.')
        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get("no_mail_to_attendees"):
            return False
        if not mail_template:
            _logger.warning("No template passed to %s notification process. Skipped.", self)
            return False

        # get ics file for all meetings
        ics_files = self.mapped('event_id')._get_ics_file()

        for attendee in self:
            if attendee.email and attendee.partner_id != self.env.user.partner_id:
                event_id = attendee.event_id.id
                ics_file = ics_files.get(event_id)

                attachment_values = []
                if ics_file:
                    attachment_values = [
                        (0, 0, {'name': 'invitation.ics',
                                'mimetype': 'text/calendar',
                                'datas': base64.b64encode(ics_file)})
                    ]
                body = mail_template._render_field(
                    'body_html',
                    attendee.ids,
                    compute_lang=True,
                    post_process=True)[attendee.id]
                subject = mail_template._render_field(
                    'subject',
                    attendee.ids,
                    compute_lang=True)[attendee.id]
                attendee.event_id.with_context(no_document=True).sudo().message_notify(
                    email_from=attendee.event_id.user_id.email_formatted or self.env.user.email_formatted,
                    author_id=attendee.event_id.user_id.partner_id.id or self.env.user.partner_id.id,
                    body=body,
                    subject=subject,
                    partner_ids=attendee.partner_id.ids,
                    email_layout_xmlid='mail.mail_notification_light',
                    attachment_ids=attachment_values,
                    force_send=force_send)

    def do_tentative(self):
        """ Makes event invitation as Tentative. """
        return self.write({'state': 'tentative'})

    def do_accept(self):
        """ Marks event invitation as Accepted. """
        for attendee in self:
            attendee.event_id.message_post(
                author_id=attendee.partner_id.id,
                body=_("%s has accepted the invitation") % (attendee.common_name),
                subtype_xmlid="calendar.subtype_invitation",
            )
        return self.write({'state': 'accepted'})

    def do_decline(self):
        """ Marks event invitation as Declined. """
        for attendee in self:
            attendee.event_id.message_post(
                author_id=attendee.partner_id.id,
                body=_("%s has declined the invitation") % (attendee.common_name),
                subtype_xmlid="calendar.subtype_invitation",
            )
        return self.write({'state': 'declined'})
