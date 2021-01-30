# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Attendee(models.Model):
    """ Calendar Attendee Information """
    _name = 'calendar.attendee'
    _rec_name = 'common_name'
    _description = 'Calendar Attendee Information'

    def _default_access_token(self):
        return uuid.uuid4().hex

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    event_id = fields.Many2one(
        'calendar.event', 'Meeting linked', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Contact', required=True, readonly=True)
    state = fields.Selection(STATE_SELECTION, string='Status', readonly=True, default='needsAction',
                             help="Status of the attendee's participation")
    common_name = fields.Char('Common name', compute='_compute_common_name', store=True)
    email = fields.Char('Email', related='partner_id.email', help="Email of Invited Person")
    availability = fields.Selection(
        [('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly=True)
    access_token = fields.Char('Invitation Token', default=_default_access_token)
    recurrence_id = fields.Many2one('calendar.recurrence', related='event_id.recurrence_id')

    @api.depends('partner_id', 'partner_id.name', 'email')
    def _compute_common_name(self):
        for attendee in self:
            attendee.common_name = attendee.partner_id.name or attendee.email

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('partner_id') == self.env.user.partner_id.id:
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

    def _subscribe_partner(self):
        for event in self.event_id:
            partners = (event.attendee_ids & self).partner_id - event.message_partner_ids
            # current user is automatically added as followers, don't add it twice.
            partners -= self.env.user.partner_id
            event.message_subscribe(partner_ids=partners.ids)

    def _unsubscribe_partner(self):
        for event in self.event_id:
            partners = (event.attendee_ids & self).partner_id & event.message_partner_ids
            event.message_unsubscribe(partner_ids=partners.ids)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    def _send_mail_to_attendees(self, template_xmlid, force_send=False, ignore_recurrence=False):
        """ Send mail for event invitation to event attendees.
            :param template_xmlid: xml id of the email template to use to send the invitation
            :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
            :param ignore_recurrence: ignore event recurrence
        """
        res = False

        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get("no_mail_to_attendees"):
            return res

        calendar_view = self.env.ref('calendar.view_calendar_event_calendar')
        invitation_template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not invitation_template:
            _logger.warning("Template %s could not be found. %s not notified." % (template_xmlid, self))
            return
        # get ics file for all meetings
        ics_files = self.mapped('event_id')._get_ics_file()

        # prepare rendering context for mail template
        colors = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }
        rendering_context = dict(self._context)
        rendering_context.update({
            'colors': colors,
            'ignore_recurrence': ignore_recurrence,
            'action_id': self.env['ir.actions.act_window'].sudo().search([('view_id', '=', calendar_view.id)], limit=1).id,
            'dbname': self._cr.dbname,
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://localhost:8069'),
        })

        for attendee in self:
            if attendee.email and attendee.partner_id != self.env.user.partner_id:
                # FIXME: is ics_file text or bytes?
                event_id = attendee.event_id.id
                ics_file = ics_files.get(event_id)

                attachment_values = []
                if ics_file:
                    attachment_values = [
                        (0, 0, {'name': 'invitation.ics',
                                'mimetype': 'text/calendar',
                                'datas': base64.b64encode(ics_file)})
                    ]
                body = invitation_template.with_context(rendering_context)._render_field(
                    'body_html',
                    attendee.ids,
                    compute_lang=True,
                    post_process=True)[attendee.id]
                subject = invitation_template._render_field(
                    'subject',
                    attendee.ids,
                    compute_lang=True)[attendee.id]
                attendee.event_id.with_context(no_document=True).message_notify(
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
                body=_("%s has accepted invitation") % (attendee.common_name),
                subtype_xmlid="calendar.subtype_invitation")
        return self.write({'state': 'accepted'})

    def do_decline(self):
        """ Marks event invitation as Declined. """
        for attendee in self:
            attendee.event_id.message_post(
                body=_("%s has declined invitation") % (attendee.common_name),
                subtype_xmlid="calendar.subtype_invitation")
        return self.write({'state': 'declined'})
