import logging
import uuid

from base64 import b64encode

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CalendarAttendee(models.Model):
    _name = "calendar.attendee_bis"
    _description = "Calendar Attendee"
    _order = "partner_id desc, id"

    def _default_access_token(self):
        return uuid.uuid4().hex

    timeslot_id = fields.Many2one('calendar.timeslot', required=True, ondelete='cascade', copy=False)
    partner_id = fields.Many2one('res.partner')
    email = fields.Char('E-Mail', store=True, compute='_compute_email', copy=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
    access_token = fields.Char('Invitation Token', default=_default_access_token, copy=False)
    state = fields.Selection([
        ('maybe', 'Maybe'),
        ('no', 'No'),
        ('yes', 'Yes'),
    ], string='Status', copy=False)

    _sql_constraints = [
        ('has_attendee', 'check(partner_id IS NOT NULL OR email IS NOT NULL)', 'The attendee should be linked to an email or an user'),
    ]

    def _compute_display_name(self):
        for attendee in self:
            attendee.display_name = attendee.partner_id.display_name or attendee.email

    def _compute_email(self):
        for attendee in self:
            attendee.email = attendee.partner_id.email or attendee.email

    @api.depends('email')
    def _compute_partner_id(self):
        for attendee in self:
            if not attendee.partner_id and attendee.email:
                attendee.partner_id = self.env['res.partner'].search([('email', '=', attendee.email)], limit=1)

    def do_accept(self):
        return self.write({'state': 'yes'})

    def do_decline(self):
        return self.write({'state': 'no'})

    def _send_mail(self, mail_template, force_send=False):
        """ Send mail for event invitation to event attendees.
            :param mail_template: a mail.template record
            :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        """
        if not mail_template:
            _logger.warning("No template passed to %s notification process. Skipped.", self)
            return False
        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get("no_mail_to_attendees"):
            return False

        attendees = self.filtered(lambda a: a.email and a._should_notify_attendee())

        ics_files = attendees.mapped('timeslot_id')._get_ics()
        ics_attachements_ids = {
            ts_id: self.env['ir.attachment'].create({
                    'datas': b64encode(ics_file),
                    'description': 'invitation.ics',
                    'mimetype': 'text/calendar',
                    'name': 'invitation.ics',
                }).ids
            for ts_id, ics_file in ics_files.items()
        }

        body_renders = mail_template._render_field('body_html', attendees.ids, compute_lang=True)
        subject_renders = mail_template._render_field('subject', attendees.ids, compute_lang=True)

        for attendee in attendees:
            attendee.event_id.with_context(no_document=True).sudo().message_notify(
                email_from=attendee.timeslot_id.partner_id.email_formatted or self.env.user.email_formatted,
                author_id=attendee.timeslot_id.partner_id.id,
                body=body_renders[attendee.id],
                subject=subject_renders[attendee.id],
                partner_ids=attendee.partner_id.ids,
                email_layout_xmlid='mail.mail_notification_light',
                attachment_ids=mail_template.attachment_ids.ids + ics_attachements_ids.get(attendee.timeslot_id.id, []),
                force_send=force_send,
            )
