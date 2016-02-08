# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

import pytz

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class CalendarAttendee(models.Model):
    """
    Calendar Attendee Information
    """
    _name = 'calendar.attendee'
    _rec_name = 'cn'
    _description = 'Attendee information'

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    state = fields.Selection(STATE_SELECTION, string='Status', default='needsAction', readonly=True, help="Status of the attendee's participation")
    cn = fields.Char(compute='_compute_data', string='Common name', store=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly="True")
    email = fields.Char(help="Email of Invited Person")
    availability = fields.Selection([('free', 'Free'), ('busy', 'Busy')], string='Free/Busy', readonly="True")
    access_token = fields.Char('Invitation Token')
    event_id = fields.Many2one('calendar.event', string='Meeting linked', ondelete='cascade')

    @api.depends('partner_id', 'email', 'partner_id.name')
    def _compute_data(self):
        """
        Compute data on function fields for attendee values.
        """
        for attdata in self:
            if attdata.partner_id:
                attdata.cn = attdata.partner_id.name or False
            else:
                attdata.cn = attdata.email or ''

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Make entry on email and availability on change of partner_id field.
        """
        self.email = self.partner_id.email

    @api.multi
    def get_ics_file(self, event_obj):
        """
        Returns iCalendar file for the event invitation.
        @param event_obj: event object (browse record)
        """
        res = None

        def ics_datetime(idate, allday=False):
            if idate:
                if allday:
                    return fields.Date.from_string(idate)
                else:
                    return fields.Datetime.from_string(idate).replace(tzinfo=pytz.timezone('UTC'))
            return False

        try:
            # FIXME: why isn't this in CalDAV?
            import vobject
        except ImportError:
            return res

        cal = vobject.iCalendar()
        event = cal.add('vevent')
        if not event_obj.start or not event_obj.stop:
            raise UserError(_("First you have to specify the date of the invitation."))
        event.add('created').value = ics_datetime(fields.Datetime.now())
        event.add('dtstart').value = ics_datetime(event_obj.start, event_obj.allday)
        event.add('dtend').value = ics_datetime(event_obj.stop, event_obj.allday)
        event.add('summary').value = event_obj.name
        if event_obj.description:
            event.add('description').value = event_obj.description
        if event_obj.location:
            event.add('location').value = event_obj.location
        if event_obj.rrule:
            event.add('rrule').value = event_obj.rrule

        if event_obj.alarm_ids:
            for alarm in event_obj.alarm_ids:
                valarm = event.add('valarm')
                interval = alarm.interval
                duration = alarm.duration
                trigger = valarm.add('TRIGGER')
                trigger.params['related'] = ["START"]
                if interval == 'days':
                    delta = timedelta(days=duration)
                elif interval == 'hours':
                    delta = timedelta(hours=duration)
                elif interval == 'minutes':
                    delta = timedelta(minutes=duration)
                trigger.value = delta
                valarm.add('DESCRIPTION').value = alarm.name or 'Odoo'
        for attendee in event_obj.attendee_ids:
            attendee_add = event.add('attendee')
            attendee_add.value = 'MAILTO:' + (attendee.email or '')
        res = cal.serialize()
        return res

    @api.multi
    def _send_mail_to_attendees(self, email_from=tools.config.get('email_from', False),
                                template_xmlid='calendar_template_meeting_invitation', force=False):
        """
        Send mail for event invitation to event attendees.
        @param email_from: email address for user sending the mail
        @param force: If set to True, email will be sent to user himself. Usefull for example for alert, ...
        """
        res = False
        mail_ids = []

        if self.env['ir.config_parameter'].get_param('calendar.block_mail') or self.env.context.get("no_mail_to_attendees"):
            return res

        Mail = self.env['mail.mail']
        local_context = self.env.context.copy()
        color = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }

        Template = self.env.ref('calendar.%s' % template_xmlid)
        act_id = self.env.ref('calendar.view_calendar_event_calendar').id
        local_context.update({
            'color': color,
            'action_id': self.env['ir.actions.act_window'].search([('view_id', '=', act_id)], limit=1).id,
            'dbname': self.env.cr.dbname,
            'base_url': self.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069')
        })

        for attendee in self:
            if attendee.email and email_from and (attendee.email != email_from or force):
                ics_file = self.get_ics_file(attendee.event_id)
                mail_id = Template.with_context(local_context).send_mail(attendee.id)

                vals = {}
                if ics_file:
                    vals['attachment_ids'] = [(0, 0, {'name': 'invitation.ics',
                                                      'datas_fname': 'invitation.ics',
                                                      'datas': str(ics_file).encode('base64')})]
                vals['model'] = None  # We don't want to have the mail in the tchatter while in queue!
                the_mailmess = Mail.browse(mail_id).mail_message_id
                the_mailmess.write(vals)
                mail_ids.append(mail_id)

        if mail_ids:
            res = Mail.browse(mail_ids).send()
        return res

    @api.multi
    def do_tentative(self):
        """
        Makes event invitation as Tentative.
        """
        self.state = 'tentative'
        return True

    @api.multi
    def do_accept(self):
        """
        Marks event invitation as Accepted.
        """
        self.state = 'accepted'
        for attendee in self:
            attendee.event_id.message_post(body=_("%s has accepted invitation") % (attendee.cn), subtype="calendar.subtype_invitation")
        return True

    @api.multi
    def do_decline(self):
        """
        Marks event invitation as Declined.
        """
        self.state = 'declined'
        for attendee in self:
            attendee.event_id.message_post(body=_("%s has declined invitation") % (attendee.cn), subtype="calendar.subtype_invitation")
        return True

    @api.model
    def create(self, vals):
        if not vals.get("email") and vals.get("cn"):
            cnval = vals.get("cn").split(':')
            email = filter(lambda x: '@' in x, cnval)
            vals['email'] = email and email[0] or ''
        return super(CalendarAttendee, self).create(vals)
