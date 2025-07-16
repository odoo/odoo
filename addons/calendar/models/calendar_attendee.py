# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import base64
import logging

from collections import defaultdict
from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context
from odoo.tools import split_every

_logger = logging.getLogger(__name__)


class CalendarAttendee(models.Model):
    """ Calendar Attendee Information """
    _name = 'calendar.attendee'
    _rec_name = 'common_name'
    _description = 'Calendar Attendee Information'
    _order = 'create_date ASC'

    def _default_access_token(self):
        return uuid.uuid4().hex

    STATE_SELECTION = [
        ('accepted', 'Yes'),
        ('declined', 'No'),
        ('tentative', 'Maybe'),
        ('needsAction', 'Needs Action'),
    ]

    # event
    event_id = fields.Many2one('calendar.event', 'Meeting linked', required=True, index=True, ondelete='cascade')
    recurrence_id = fields.Many2one('calendar.recurrence', related='event_id.recurrence_id')
    # attendee
    partner_id = fields.Many2one('res.partner', 'Attendee', required=True, readonly=True, ondelete='cascade')
    email = fields.Char('Email', related='partner_id.email')
    phone = fields.Char('Phone', related='partner_id.phone')
    common_name = fields.Char('Common name', compute='_compute_common_name', store=True)
    access_token = fields.Char('Invitation Token', default=_default_access_token)
    mail_tz = fields.Selection(_tz_get, compute='_compute_mail_tz', help='Timezone used for displaying time in the mail template')
    # state
    state = fields.Selection(STATE_SELECTION, string='Status', default='needsAction')
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
        return super().create(vals_list)

    def unlink(self):
        self._unsubscribe_partner()
        return super().unlink()

    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    def _unsubscribe_partner(self):
        for event in self.event_id:
            partners = (event.attendee_ids & self).partner_id & event.message_partner_ids
            event.message_unsubscribe(partner_ids=partners.ids)

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    @api.model
    def _mail_template_default_values(self):
        return {
            "email_from": "{{ (object.event_id.user_id.email_formatted or user.email_formatted or '') }}",
            "email_to": False,
            "partner_to": False,
            "lang": "{{ object.partner_id.lang }}",
            "use_default_to": True,
        }

    def _message_add_default_recipients(self):
        # override: partner_id being the only stored field, we can currently
        # simplify computation, we have no other choice than relying on it
        return {
            attendee.id: {
                'partners': attendee.partner_id,
                'email_to_lst': [],
                'email_cc_lst': [],
            } for attendee in self
        }

    def _send_invitation_emails(self):
        """ Hook to be able to override the invitation email sending process.
         Notably inside appointment to use a different mail template from the appointment type. """
        self._notify_attendees(
            self.env.ref('calendar.calendar_template_meeting_invitation', raise_if_not_found=False),
            force_send=True,
        )

    def _notify_attendees(self, mail_template, notify_author=False, force_send=False):
        """ Notify attendees about event main changes (invite, cancel, ...) based
        on template.

        :param mail_template: a mail.template record
        :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        """
        # TDE FIXME: check this
        if force_send:
            force_send_limit = int(self.env['ir.config_parameter'].sudo().get_param('mail.mail_force_send_limit', 100))
        notified_attendees_ids = set(self.ids)
        for event, attendees in self.grouped('event_id').items():
            if event._skip_send_mail_status_update():
                notified_attendees_ids -= set(attendees.ids)
        notified_attendees = self.browse(notified_attendees_ids)
        if isinstance(mail_template, str):
            raise ValueError('Template should be a template record, not an XML ID anymore.')
        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self.env.context.get("no_mail_to_attendees"):
            return False
        if not mail_template:
            _logger.warning("No template passed to %s notification process. Skipped.", self)
            return False

        # get ics file for all meetings
        ics_files = notified_attendees.event_id._get_ics_file()

        # If the mail template has attachments, prepare copies for each attendee (to be added to each attendee's mail)
        if mail_template.attachment_ids:

            # Setting res_model to ensure attachments are linked to the msg (otherwise only internal users are allowed link attachments)
            attachments_values = [a.copy_data({'res_id': 0, 'res_model': 'mail.compose.message'})[0] for a in mail_template.attachment_ids]
            attachments_values *= len(self)
            attendee_attachment_ids = self.env['ir.attachment'].create(attachments_values).ids

            # Map attendees to their respective attachments
            template_attachment_count = len(mail_template.attachment_ids)
            attendee_id_attachment_id_map = dict(zip(self.ids, split_every(template_attachment_count, attendee_attachment_ids, list)))

        mail_messages = self.env['mail.message']
        for attendee in notified_attendees:
            if attendee.email and attendee._should_notify_attendee(notify_author=notify_author):
                event_id = attendee.event_id.id
                ics_file = ics_files.get(event_id)

                # Add template attachments copies to the attendee's email, if available
                attachment_ids = attendee_id_attachment_id_map[attendee.id] if mail_template.attachment_ids else []

                if ics_file:
                    context = {
                        **clean_context(self.env.context),
                        'no_document': True,  # An ICS file must not create a document
                    }
                    attachment_ids += self.env['ir.attachment'].with_context(context).create({
                        'datas': base64.b64encode(ics_file),
                        'description': 'invitation.ics',
                        'mimetype': 'text/calendar',
                        'res_id': 0,
                        'res_model': 'mail.compose.message',
                        'name': 'invitation.ics',
                    }).ids

                body = mail_template._render_field(
                    'body_html',
                    attendee.ids,
                    compute_lang=True)[attendee.id]
                subject = mail_template._render_field(
                    'subject',
                    attendee.ids,
                    compute_lang=True)[attendee.id]
                mail_messages += attendee.event_id.with_context(no_document=True).sudo().message_notify(
                    email_from=attendee.event_id.user_id.email_formatted or self.env.user.email_formatted,
                    author_id=attendee.event_id.user_id.partner_id.id or self.env.user.partner_id.id,
                    body=body,
                    subject=subject,
                    notify_author=notify_author,
                    partner_ids=attendee.partner_id.ids,
                    email_layout_xmlid='mail.mail_notification_light',
                    attachment_ids=attachment_ids,
                    force_send=False,
                )
        # batch sending at the end
        if force_send and len(notified_attendees) < force_send_limit:
            mail_messages.sudo().mail_ids.send_after_commit()

    def _should_notify_attendee(self, notify_author=False):
        """ Utility method that determines if the attendee should be notified.
            By default, we do not want to notify (aka no message and no mail) the current user
            if he is part of the attendees. But for reminders, mail_notify_author could be forced
            (Override in appointment to ignore that rule and notify all attendees if it's an appointment)
        """
        self.ensure_one()
        partner_not_sender = self.partner_id != self.env.user.partner_id
        return partner_not_sender or notify_author

    # ------------------------------------------------------------
    # STATE MANAGEMENT
    # ------------------------------------------------------------

    def do_tentative(self):
        """ Makes event invitation as Tentative. """
        return self.write({'state': 'tentative'})

    def do_accept(self):
        """ Marks event invitation as Accepted. """
        for attendee in self:
            attendee.event_id.message_post(
                author_id=attendee.partner_id.id,
                body=_("%s has accepted the invitation", attendee.common_name),
                subtype_xmlid="calendar.subtype_invitation",
            )
        return self.write({'state': 'accepted'})

    def do_decline(self):
        """ Marks event invitation as Declined. """
        for attendee in self:
            attendee.event_id.message_post(
                author_id=attendee.partner_id.id,
                body=_("%s has declined the invitation", attendee.common_name),
                subtype_xmlid="calendar.subtype_invitation",
            )
        return self.write({'state': 'declined'})
