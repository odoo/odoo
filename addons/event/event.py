# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class event_type(osv.osv):
    """ Event Type """
    _name = 'event.type'
    _description = __doc__
    _columns = {
        'name': fields.char('Event Type', size=64, required=True),
        'default_reply_to': fields.char('Default Reply-To', size=64,help="The email address of the organizer which is put in the 'Reply-To' of all emails sent automatically at event or registrations confirmation. You can also put your email address of your mail gateway if you use one." ),
        'default_email_event': fields.many2one('email.template','Event Confirmation Email', help="It will select this default confirmation event mail value when you choose this event"),
        'default_email_registration': fields.many2one('email.template','Registration Confirmation Email', help="It will select this default confirmation registration mail value when you choose this event"),
        'default_registration_min': fields.integer('Default Minimum Registration', help="It will select this default minimum value when you choose this event"),
        'default_registration_max': fields.integer('Default Maximum Registration', help="It will select this default maximum value when you choose this event"),
    }
    _defaults = {
        'default_registration_min': 0,
        'default_registration_max': 0,
    }

event_type()

class event_event(osv.osv):
    """Event"""
    _name = 'event.event'
    _description = __doc__
    _order = 'date_begin'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []

        if isinstance(ids, (long, int)):
            ids = [ids]

        res = []
        for record in self.browse(cr, uid, ids, context=context):
            date = record.date_begin.split(" ")[0]
            date_end = record.date_end.split(" ")[0]
            if date != date_end:
                date += ' - ' + date_end
            display_name = record.name + ' (' + date + ')'
            res.append((record['id'], display_name))
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """ Reset the state and the registrations while copying an event
        """
        if not default:
            default = {}
        default.update({
            'state': 'draft',
            'registration_ids': False,
        })
        return super(event_event, self).copy(cr, uid, id, default=default, context=context)

    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        registration = self.pool.get('event.registration')
        reg_ids = registration.search(cr, uid, [('event_id','in',ids)], context=context)
        for event_reg in registration.browse(cr,uid,reg_ids,context=context):
            if event_reg.state == 'done':
                raise osv.except_osv(_('Error!'),_("You have already set a registration for this event as 'Attended'. Please reset it to draft if you want to cancel this event.") )
        registration.write(cr, uid, reg_ids, {'state': 'cancel'}, context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def button_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def check_registration_limits(self, cr, uid, ids, context=None):
        for self.event in self.browse(cr, uid, ids, context=context):
            total_confirmed = self.event.register_current
            if total_confirmed < self.event.register_min or total_confirmed > self.event.register_max and self.event.register_max!=0:
                raise osv.except_osv(_('Error!'),_("The total of confirmed registration for the event '%s' does not meet the expected minimum/maximum. Please reconsider those limits before going further.") % (self.event.name))

    def check_registration_limits_before(self, cr, uid, ids, no_of_registration, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            available_seats = event.register_avail
            if available_seats and no_of_registration > available_seats:
                raise osv.except_osv(_('Warning!'),_("Only %d Seats are Available!") % (available_seats))
            elif available_seats == 0:
                raise osv.except_osv(_('Warning!'),_("No Tickets Available!"))

    def confirm_event(self, cr, uid, ids, context=None):
        register_pool = self.pool.get('event.registration')
        if self.event.email_confirmation_id:
        #send reminder that will confirm the event for all the people that were already confirmed
            reg_ids = register_pool.search(cr, uid, [
                               ('event_id', '=', self.event.id),
                               ('state', 'not in', ['draft', 'cancel'])], context=context)
            register_pool.mail_user_confirm(cr, uid, reg_ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def button_confirm(self, cr, uid, ids, context=None):
        """ Confirm Event and send confirmation email to all register peoples
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check_registration_limits(cr, uid, ids, context=context)
        return self.confirm_event(cr, uid, ids, context=context)

    def _get_register(self, cr, uid, ids, fields, args, context=None):
        """Get Confirm or uncofirm register value.
        @param ids: List of Event registration type's id
        @param fields: List of function fields(register_current and register_prospect).
        @param context: A standard dictionary for contextual values
        @return: Dictionary of function fields value.
        """
        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = {}
            reg_open = reg_done = reg_draft =0
            for registration in event.registration_ids:
                if registration.state == 'open':
                    reg_open += registration.nb_register
                elif registration.state == 'done':
                    reg_done += registration.nb_register
                elif registration.state == 'draft':
                    reg_draft += registration.nb_register
            for field in fields:
                number = 0
                if field == 'register_current':
                    number = reg_open
                elif field == 'register_attended':
                    number = reg_done
                elif field == 'register_prospect':
                    number = reg_draft
                elif field == 'register_avail':
                    #the number of ticket is unlimited if the event.register_max field is not set.
                    #In that cas we arbitrary set it to 9999, it is used in the kanban view to special case the display of the 'subscribe' button
                    number = event.register_max - reg_open if event.register_max != 0 else 9999
                res[event.id][field] = number
        return res

    def _subscribe_fnc(self, cr, uid, ids, fields, args, context=None):
        """This functional fields compute if the current user (uid) is already subscribed or not to the event passed in parameter (ids)
        """
        register_pool = self.pool.get('event.registration')
        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = False
            curr_reg_id = register_pool.search(cr, uid, [('user_id', '=', uid), ('event_id', '=' ,event.id)], context=context)
            if curr_reg_id:
                for reg in register_pool.browse(cr, uid, curr_reg_id, context=context):
                    if reg.state in ('open','done'):
                        res[event.id]= True
                        continue
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True, readonly=False, states={'done': [('readonly', True)]}),
        'user_id': fields.many2one('res.users', 'Responsible User', readonly=False, states={'done': [('readonly', True)]}),
        'type': fields.many2one('event.type', 'Type of Event', readonly=False, states={'done': [('readonly', True)]}),
        'register_max': fields.integer('Maximum Registrations', help="You can for each event define a maximum registration level. If you have too much registrations you are not able to confirm your event. (put 0 to ignore this rule )", readonly=True, states={'draft': [('readonly', False)]}),
        'register_min': fields.integer('Minimum Registrations', help="You can for each event define a minimum registration level. If you do not enough registrations you are not able to confirm your event. (put 0 to ignore this rule )", readonly=True, states={'draft': [('readonly', False)]}),
        'register_current': fields.function(_get_register, string='Confirmed Registrations', multi='register_numbers'),
        'register_avail': fields.function(_get_register, string='Available Registrations', multi='register_numbers',type='integer'),
        'register_prospect': fields.function(_get_register, string='Unconfirmed Registrations', multi='register_numbers'),
        'register_attended': fields.function(_get_register, string='# of Participations', multi='register_numbers'),
        'registration_ids': fields.one2many('event.registration', 'event_id', 'Registrations', readonly=False, states={'done': [('readonly', True)]}),
        'date_begin': fields.datetime('Start Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_end': fields.datetime('End Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Unconfirmed'),
            ('cancel', 'Cancelled'),
            ('confirm', 'Confirmed'),
            ('done', 'Done')],
            'Status', readonly=True, required=True,
            track_visibility='onchange',
            help='If event is created, the status is \'Draft\'.If event is confirmed for the particular dates the status is set to \'Confirmed\'. If the event is over, the status is set to \'Done\'.If event is cancelled the status is set to \'Cancelled\'.'),
        'email_registration_id' : fields.many2one('email.template','Registration Confirmation Email', help='This field contains the template of the mail that will be automatically sent each time a registration for this event is confirmed.'),
        'email_confirmation_id' : fields.many2one('email.template','Event Confirmation Email', help="If you set an email template, each participant will receive this email announcing the confirmation of the event."),
        'reply_to': fields.char('Reply-To Email', size=64, readonly=False, states={'done': [('readonly', True)]}, help="The email address of the organizer is likely to be put here, with the effect to be in the 'Reply-To' of the mails sent automatically at event or registrations confirmation. You can also put the email address of your mail gateway if you use one."),
        'main_speaker_id': fields.many2one('res.partner','Main Speaker', readonly=False, states={'done': [('readonly', True)]}, help="Speaker who will be giving speech at the event."),
        'address_id': fields.many2one('res.partner','Location Address', readonly=False, states={'done': [('readonly', True)]}),
        'street': fields.related('address_id','street',type='char',string='Street'),
        'street2': fields.related('address_id','street2',type='char',string='Street2'),
        'state_id': fields.related('address_id','state_id',type='many2one', relation="res.country.state", string='State'),
        'zip': fields.related('address_id','zip',type='char',string='zip'),
        'city': fields.related('address_id','city',type='char',string='city'),
        'speaker_confirmed': fields.boolean('Speaker Confirmed', readonly=False, states={'done': [('readonly', True)]}),
        'country_id': fields.related('address_id', 'country_id',
                    type='many2one', relation='res.country', string='Country', readonly=False, states={'done': [('readonly', True)]}),
        'note': fields.text('Description', readonly=False, states={'done': [('readonly', True)]}),
        'company_id': fields.many2one('res.company', 'Company', required=False, change_default=True, readonly=False, states={'done': [('readonly', True)]}),
        'is_subscribed' : fields.function(_subscribe_fnc, type="boolean", string='Subscribed'),
    }
    _defaults = {
        'state': 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'event.event', context=c),
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def subscribe_to_event(self, cr, uid, ids, context=None):
        register_pool = self.pool.get('event.registration')
        user_pool = self.pool.get('res.users')
        num_of_seats = int(context.get('ticket', 1))
        self.check_registration_limits_before(cr, uid, ids, num_of_seats, context=context)
        user = user_pool.browse(cr, uid, uid, context=context)
        curr_reg_ids = register_pool.search(cr, uid, [('user_id', '=', user.id), ('event_id', '=' , ids[0])])
        #the subscription is done with SUPERUSER_ID because in case we share the kanban view, we want anyone to be able to subscribe
        if not curr_reg_ids:
            curr_reg_ids = [register_pool.create(cr, SUPERUSER_ID, {'event_id': ids[0] ,'email': user.email, 'name':user.name, 'user_id': user.id, 'nb_register': num_of_seats}, context=context)]
        else:
            register_pool.write(cr, uid, curr_reg_ids, {'nb_register': num_of_seats}, context=context)
        return register_pool.confirm_registration(cr, SUPERUSER_ID, curr_reg_ids, context=context)

    def unsubscribe_to_event(self, cr, uid, ids, context=None):
        register_pool = self.pool.get('event.registration')
        #the unsubscription is done with SUPERUSER_ID because in case we share the kanban view, we want anyone to be able to unsubscribe
        curr_reg_ids = register_pool.search(cr, SUPERUSER_ID, [('user_id', '=', uid), ('event_id', '=', ids[0])], context=context)
        return register_pool.button_reg_cancel(cr, SUPERUSER_ID, curr_reg_ids, context=context)

    def _check_closing_date(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.date_end < event.date_begin:
                return False
        return True

    _constraints = [
        (_check_closing_date, 'Error ! Closing Date cannot be set before Beginning Date.', ['date_end']),
    ]

    def onchange_event_type(self, cr, uid, ids, type_event, context=None):
        values = {}
        if type_event:
            type_info =  self.pool.get('event.type').browse(cr,uid,type_event, context=context)
            dic ={
              'reply_to': type_info.default_reply_to,
              'email_registration_id': type_info.default_email_registration.id,
              'email_confirmation_id': type_info.default_email_event.id,
              'register_min': type_info.default_registration_min,
              'register_max': type_info.default_registration_max,
            }
            values.update(dic)
        return values

    def on_change_address_id(self, cr, uid, ids, address_id, context=None):
        values = {}
        if not address_id:
            return values
        address = self.pool.get('res.partner').browse(cr, uid, address_id, context=context)
        values.update({
            'street' : address.street,
            'street2' : address.street2,
            'city' : address.city,
            'country_id' : address.country_id and address.country_id.id or False,
            'state_id' : address.state_id and address.state_id.id or False,
            'zip' : address.zip,
        })
        return {'value' : values}

    def onchange_start_date(self, cr, uid, ids, date_begin=False, date_end=False, context=None):
        res = {'value':{}}
        if date_end:
            return res
        if date_begin and isinstance(date_begin, str):
            date_begin = datetime.strptime(date_begin, "%Y-%m-%d %H:%M:%S")
            date_end = date_begin + timedelta(hours=1)
            res['value'] = {'date_end': date_end.strftime("%Y-%m-%d %H:%M:%S")}
        return res


class event_registration(osv.osv):
    """Event Registration"""
    _name= 'event.registration'
    _description = __doc__
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _columns = {
        'id': fields.integer('ID'),
        'origin': fields.char('Source Document', size=124,readonly=True,help="Reference of the sales order which created the registration"),
        'nb_register': fields.integer('Number of Participants', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'event_id': fields.many2one('event.event', 'Event', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done': [('readonly', True)]}),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'date_closed': fields.datetime('Attended Date', readonly=True),
        'date_open': fields.datetime('Registration Date', readonly=True),
        'reply_to': fields.related('event_id','reply_to',string='Reply-to Email', type='char', size=128, readonly=True,),
        'log_ids': fields.one2many('mail.message', 'res_id', 'Logs', domain=[('model','=',_name)]),
        'event_end_date': fields.related('event_id','date_end', type='datetime', string="Event End Date", readonly=True),
        'event_begin_date': fields.related('event_id', 'date_begin', type='datetime', string="Event Start Date", readonly=True),
        'user_id': fields.many2one('res.users', 'User', states={'done': [('readonly', True)]}),
        'company_id': fields.related('event_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft', 'Unconfirmed'),
                                    ('cancel', 'Cancelled'),
                                    ('open', 'Confirmed'),
                                    ('done', 'Attended')], 'Status',
                                    track_visibility='onchange',
                                    size=16, readonly=True),
        'email': fields.char('Email', size=64),
        'phone': fields.char('Phone', size=64),
        'name': fields.char('Name', size=128, select=True),
    }
    _defaults = {
        'nb_register': 1,
        'state': 'draft',
    }
    _order = 'name, create_date desc'

    def do_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def confirm_registration(self, cr, uid, ids, context=None):
        for reg in self.browse(cr, uid, ids, context=context or {}):
            self.pool.get('event.event').message_post(cr, uid, [reg.event_id.id], body=_('New registration confirmed: %s.') % (reg.name or '', ),subtype="event.mt_event_registration", context=context)
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def registration_open(self, cr, uid, ids, context=None):
        """ Open Registration
        """
        event_obj = self.pool.get('event.event')
        for register in  self.browse(cr, uid, ids, context=context):
            event_id = register.event_id.id
            no_of_registration = register.nb_register
            event_obj.check_registration_limits_before(cr, uid, [event_id], no_of_registration, context=context)
        res = self.confirm_registration(cr, uid, ids, context=context)
        self.mail_user(cr, uid, ids, context=context)
        return res

    def button_reg_close(self, cr, uid, ids, context=None):
        """ Close Registration
        """
        if context is None:
            context = {}
        today = fields.datetime.now()
        for registration in self.browse(cr, uid, ids, context=context):
            if today >= registration.event_id.date_begin:
                values = {'state': 'done', 'date_closed': today}
                self.write(cr, uid, ids, values)
            else:
                raise osv.except_osv(_('Error!'), _("You must wait for the starting day of the event to do this action."))
        return True

    def button_reg_cancel(self, cr, uid, ids, context=None, *args):
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def mail_user(self, cr, uid, ids, context=None):
        """
        Send email to user with email_template when registration is done
        """
        for registration in self.browse(cr, uid, ids, context=context):
            if registration.event_id.state == 'confirm' and registration.event_id.email_confirmation_id.id:
                self.mail_user_confirm(cr, uid, ids, context=context)
            else:
                template_id = registration.event_id.email_registration_id.id
                if template_id:
                    self.pool.get('email.template').send_mail(cr,uid,template_id,registration.id, context=context)
        return True

    def mail_user_confirm(self, cr, uid, ids, context=None):
        """
        Send email to user when the event is confirmed
        """
        for registration in self.browse(cr, uid, ids, context=context):
            template_id = registration.event_id.email_confirmation_id.id
            if template_id:
                self.pool.get('email.template').send_mail(cr,uid,template_id,registration.id, context=context)
        return True

    def onchange_contact_id(self, cr, uid, ids, contact, partner, context=None):
        if not contact:
            return {}
        addr_obj = self.pool.get('res.partner')
        contact_id =  addr_obj.browse(cr, uid, contact, context=context)
        return {'value': {
            'email':contact_id.email,
            'name':contact_id.name,
            'phone':contact_id.phone,
            }}

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res_obj = self.pool.get('res.partner')
        data = {}
        if not part:
            return {'value': data}
        addr = res_obj.address_get(cr, uid, [part]).get('default', False)
        if addr:
            d = self.onchange_contact_id(cr, uid, ids, addr, part, context)
            data.update(d['value'])
        return {'value': data}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
