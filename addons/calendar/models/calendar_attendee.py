# -*- coding: utf-8 -*-

import pytz
import time
import openerp
import openerp.service.report
from datetime import timedelta
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError


class calendar_attendee(osv.Model):
    """
    Calendar Attendee Information
    """
    _name = 'calendar.attendee'
    _rec_name = 'cn'
    _description = 'Attendee information'

    def _compute_data(self, cr, uid, ids, name, arg, context=None):
        """
        Compute data on function fields for attendee values.
        @param ids: list of calendar attendee's IDs
        @param name: name of field
        @return: dictionary of form {id: {'field Name': value'}}
        """
        name = name[0]
        result = {}
        for attdata in self.browse(cr, uid, ids, context=context):
            id = attdata.id
            result[id] = {}
            if name == 'cn':
                if attdata.partner_id:
                    result[id][name] = attdata.partner_id.name or False
                else:
                    result[id][name] = attdata.email or ''
        return result

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    _columns = {
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, help="Status of the attendee's participation"),
        'cn': fields.function(_compute_data, string='Common name', type="char", multi='cn', store=True),
        'partner_id': fields.many2one('res.partner', 'Contact', readonly="True"),
        'email': fields.char('Email', help="Email of Invited Person"),
        'availability': fields.selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly="True"),
        'access_token': fields.char('Invitation Token'),
        'event_id': fields.many2one('calendar.event', 'Meeting linked', ondelete='cascade'),
    }
    _defaults = {
        'state': 'needsAction',
    }

    def copy(self, cr, uid, id, default=None, context=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        """
        Make entry on email and availability on change of partner_id field.
        @param partner_id: changed value of partner id
        """
        if not partner_id:
            return {'value': {'email': ''}}
        partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
        return {'value': {'email': partner.email}}

    def get_ics_file(self, cr, uid, event_obj, context=None):
        """
        Returns iCalendar file for the event invitation.
        @param event_obj: event object (browse record)
        @return: .ics file content
        """
        res = None

        def ics_datetime(idate, allday=False):
            if idate:
                if allday:
                    return openerp.fields.Date.from_string(idate)
                else:
                    return openerp.fields.Datetime.from_string(idate).replace(tzinfo=pytz.timezone('UTC'))
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
        event.add('created').value = ics_datetime(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
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

    def _send_mail_to_attendees(self, cr, uid, ids, email_from=tools.config.get('email_from', False),
                                template_xmlid='calendar_template_meeting_invitation', force=False, context=None):
        """
        Send mail for event invitation to event attendees.
        @param email_from: email address for user sending the mail
        @param force: If set to True, email will be sent to user himself. Usefull for example for alert, ...
        """
        res = False

        if self.pool['ir.config_parameter'].get_param(cr, uid, 'calendar.block_mail', default=False) or context.get("no_mail_to_attendees"):
            return res

        mail_ids = []
        data_pool = self.pool['ir.model.data']
        mailmess_pool = self.pool['mail.message']
        mail_pool = self.pool['mail.mail']
        template_pool = self.pool['mail.template']
        local_context = context.copy()
        color = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }

        if not isinstance(ids, (tuple, list)):
            ids = [ids]

        dummy, template_id = data_pool.get_object_reference(cr, uid, 'calendar', template_xmlid)
        dummy, act_id = data_pool.get_object_reference(cr, uid, 'calendar', "view_calendar_event_calendar")
        local_context.update({
            'color': color,
            'action_id': self.pool['ir.actions.act_window'].search(cr, uid, [('view_id', '=', act_id)], context=context)[0],
            'dbname': cr.dbname,
            'base_url': self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
        })

        for attendee in self.browse(cr, uid, ids, context=context):
            if attendee.email and email_from and (attendee.email != email_from or force):
                ics_file = self.get_ics_file(cr, uid, attendee.event_id, context=context)
                mail_id = template_pool.send_mail(cr, uid, template_id, attendee.id, context=local_context)

                vals = {}
                if ics_file:
                    vals['attachment_ids'] = [(0, 0, {'name': 'invitation.ics',
                                                      'datas_fname': 'invitation.ics',
                                                      'datas': str(ics_file).encode('base64')})]
                vals['model'] = None  # We don't want to have the mail in the tchatter while in queue!
                the_mailmess = mail_pool.browse(cr, uid, mail_id, context=context).mail_message_id
                mailmess_pool.write(cr, uid, [the_mailmess.id], vals, context=context)
                mail_ids.append(mail_id)

        if mail_ids:
            res = mail_pool.send(cr, uid, mail_ids, context=context)

        return res

    def onchange_user_id(self, cr, uid, ids, user_id, *args, **argv):
        """
        Make entry on email and availability on change of user_id field.
        @param ids: list of attendee's IDs
        @param user_id: changed value of User id
        @return: dictionary of values which put value in email and availability fields
        """
        if not user_id:
            return {'value': {'email': ''}}

        user = self.pool['res.users'].browse(cr, uid, user_id, *args)
        return {'value': {'email': user.email, 'availability': user.availability}}

    def do_tentative(self, cr, uid, ids, context=None, *args):
        """
        Makes event invitation as Tentative.
        @param ids: list of attendee's IDs
        """
        return self.write(cr, uid, ids, {'state': 'tentative'}, context)

    def do_accept(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Accepted.
        @param ids: list of attendee's IDs
        """
        if context is None:
            context = {}
        meeting_obj = self.pool['calendar.event']
        res = self.write(cr, uid, ids, {'state': 'accepted'}, context)
        for attendee in self.browse(cr, uid, ids, context=context):
            meeting_obj.message_post(cr, uid, attendee.event_id.id, body=_("%s has accepted invitation") % (attendee.cn),
                                     subtype="calendar.subtype_invitation", context=context)

        return res

    def do_decline(self, cr, uid, ids, context=None, *args):
        """
        Marks event invitation as Declined.
        @param ids: list of calendar attendee's IDs
        """
        if context is None:
            context = {}
        meeting_obj = self.pool['calendar.event']
        res = self.write(cr, uid, ids, {'state': 'declined'}, context)
        for attendee in self.browse(cr, uid, ids, context=context):
            meeting_obj.message_post(cr, uid, attendee.event_id.id, body=_("%s has declined invitation") % (attendee.cn), subtype="calendar.subtype_invitation", context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if not vals.get("email") and vals.get("cn"):
            cnval = vals.get("cn").split(':')
            email = filter(lambda x: x.__contains__('@'), cnval)
            vals['email'] = email and email[0] or ''
            vals['cn'] = vals.get("cn")
        res = super(calendar_attendee, self).create(cr, uid, vals, context=context)
        return res
