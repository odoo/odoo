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

from osv import fields, osv
import time
import netsvc
import pooler
import tools
from tools.translate import _
from crm import crm


class event_type(osv.osv):
    _name = 'event.type'
    _description= 'Event type'
    _columns = {
        'name': fields.char('Event type', size=64, required=True), 
    }
event_type()

class event(osv.osv):
    _name = 'event.event'
    _description = 'Event'
    _inherits = {'crm.case.section': 'section_id'}
    _order = 'date_begin'

    def copy(self, cr, uid, id, default=None, context=None):
        return super(event, self).copy(cr, uid, id, default={'code': self.pool.get('ir.sequence').get(cr, uid, 'event.event'), 'state': 'draft'})

    def button_draft(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'draft'})

    def button_cancel(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def button_done(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'done'})

    def button_confirm(self, cr, uid, ids, context={}):
        for eve in self.browse(cr, uid, ids):
            if eve.mail_auto_confirm:
                #send reminder that will confirm the event for all the people that were already confirmed
                reg_ids = self.pool.get('event.registration').search(cr, uid, [('event_id', '=', eve.id), ('state', 'not in', ['draft', 'cancel'])])
                if reg_ids:
                    self.pool.get('event.registration').mail_user_confirm(cr, uid, reg_ids)
        return self.write(cr, uid, ids, {'state': 'confirm'})

    def _get_register(self, cr, uid, ids, name, args, context=None):
        res={}
        for event in self.browse(cr, uid, ids, context):
            res[event.id] = {}
            state = 'draft'
            if name[0] == 'register_current':
                state = 'open'
            query = """SELECT sum(r.nb_register) 
                        from event_registration r 
                        where state=%s and event_id=%s"""

            cr.execute(query, (state, event.id, ))
            res2 = cr.fetchone()
            if res2 and res2[0]:
                res[event.id][name[0]] = res2[0]
            else:
                res[event.id][name[0]] = 0
        return res

    def write(self, cr, uid, ids, vals, *args, **kwargs):
        res = super(event, self).write(cr, uid, ids, vals, *args, **kwargs)
        if 'date_begin' in vals and vals['date_begin']:
            for eve in self.browse(cr, uid, ids):
                #change the deadlines of the registration linked to this event
                reg_ids = self.pool.get('event.registration').search(cr, uid, [('event_id', '=', eve.id)])
                if reg_ids:
                    self.pool.get('event.registration').write(cr, uid, reg_ids, {'date_deadline': vals['date_begin']})

        #change the description of the registration linked to this event
        if 'mail_auto_confirm' in vals:
            if vals['mail_auto_confirm']:
                if 'mail_confirm' not in vals:
                    for eve in self.browse(cr, uid, ids):
                        vals['mail_confirm'] = eve.mail_confirm
            else:
                vals['mail_confirm']=False
        if 'mail_confirm' in vals:
            for eve in self.browse(cr, uid, ids):
                reg_ids = self.pool.get('event.registration').search(cr, uid, [('event_id', '=', eve.id)])
                if reg_ids:
                    self.pool.get('event.registration').write(cr, uid, reg_ids, {'description': vals['mail_confirm']})
        return res

    _columns = {
        'type': fields.many2one('event.type', 'Type'), 
        'section_id': fields.many2one('crm.case.section', 'Case section', required=True), 
        'register_max': fields.integer('Maximum Registrations'), 
        'register_min': fields.integer('Minimum Registrations'), 
        'register_current': fields.function(_get_register, method=True, string='Confirmed Registrations', multi='register_current'), 
        'register_prospect': fields.function(_get_register, method=True, string='Unconfirmed Registrations', multi='register_prospect'), 
        'date_begin': fields.datetime('Beginning date', required=True), 
        'date_end': fields.datetime('Ending date', required=True), 
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, required=True, 
                                  help='If event is created, the state is \'Draft\'.\n If event is confirmed for the particular dates the state is set to \'Confirmed\'.\
                                  \nIf the event is over, the state is set to \'Done\'.\n If event is cancelled the state is set to \'Cancelled\'.'), 
        'mail_auto_registr': fields.boolean('Mail Auto Register', help='Check this box if you want to use the automatic mailing for new registration'), 
        'mail_auto_confirm': fields.boolean('Mail Auto Confirm', help='Check this box if you want ot use the automatic confirmation emailing or the reminder'), 
        'mail_registr': fields.text('Registration Email', help='This email will be sent when someone subscribes to the event.'), 
        'mail_confirm': fields.text('Confirmation Email', help="This email will be sent when the event gets confimed or when someone subscribes to a confirmed event. This is also the email sent to remind someone about the event."), 
        'product_id': fields.many2one('product.product', 'Product', required=True), 
    }

    _defaults = {
        'state': lambda *args: 'draft', 
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'event.event'), 
        'user_id': lambda self, cr, uid, ctx: uid, 
    }

event()

class event_registration(osv.osv):

    def check_confirm(self, cr, uid, ids, context):
        mod_obj = self.pool.get('ir.model.data')
        current_registration = self.browse(cr, uid, [ids[0]])[0]
        total_confirmed = current_registration.event_id.register_current + current_registration.nb_register
        if total_confirmed <= current_registration.event_id.register_max or current_registration.event_id.register_max == 0:
            self.write(cr, uid, [ids[0]], {'state': 'open'}, context=context)
            self._history(cr, uid, [ids[0]], 'Open', history=True)
            self.mail_user(cr, uid, [ids[0]])
            return True
        else:
            model_data_ids = mod_obj.search(cr, uid, [('model', '=', 'ir.ui.view'), ('name', '=', 'view_event_confirm_registration')], context=context)
            resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            context.update({'reg_id': ids[0]})
            return {
                'name': _('Confirm Registration'), 
                'context': context, 
                'view_type': 'form', 
                'view_mode': 'tree,form', 
                'res_model': 'event.confirm.registration', 
                'views': [(resource_id, 'form')], 
                'type': 'ir.actions.act_window', 
                'target': 'new', 
                'nodestroy': True
            }

    def _history(self, cr, uid, ids, keyword, history=False, email=False, context={}):
        for case in self.browse(cr, uid, ids):
            data = {
                'name': keyword, 
                'som': case.som.id, 
                'canal_id': case.canal_id.id, 
                'user_id': uid, 
            }
            obj = self.pool.get('mailgate.message')
            obj.create(cr, uid, data, context=context)
        return True

    def button_reg_close(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'done', })
        self._history(cr, uid, ids, 'Done', history=True)
        return True

    def button_reg_cancel(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'cancel', })
        self._history(cr, uid, ids, 'Cancel', history=True)
        return True

    def create(self, cr, uid, *args, **argv):
        event = self.pool.get('event.event').browse(cr, uid, args[0]['event_id'], None)
        args[0]['section_id']= event.section_id.id
        args[0]['date_deadline']= event.date_begin
        args[0]['description']= event.mail_confirm
        res = super(event_registration, self).create(cr, uid, *args, **argv)
        self._history(cr, uid, [res], 'Created', history=True)
        return res

    def write(self, cr, uid, *args, **argv):
        if 'event_id' in args[1]:
            event = self.pool.get('event.event').browse(cr, uid, args[1]['event_id'], None)
            args[1]['section_id']= event.section_id.id
            args[1]['date_deadline']= event.date_begin
            args[1]['description']= event.mail_confirm
        return super(event_registration, self).write(cr, uid, *args, **argv)

    def mail_user_confirm(self, cr, uid, ids):
        reg_ids = self.browse(cr,uid,ids)
        for reg_id in reg_ids:
            src = reg_id.event_id.reply_to or False
            dest = []
            if reg_id.email_from:
                dest += [reg_id.email_from]
            if reg_id.email_cc:
                dest += [reg_id.email_cc]
            if dest and src:
                tools.email_send(src, dest, 'Auto Confirmation: '+'['+str(reg_id.id)+']'+' '+reg_id.name, reg_id.event_id.mail_confirm, openobject_id = str(reg_id.id))
            if not src:
                raise osv.except_osv(_('Error!'), _('You must define a reply-to address in order to mail the participant. You can do this in the Mailing tab of your event. Note that this is also the place where you can configure your event to not send emails automaticly while registering'))
        return False

    def mail_user(self, cr, uid, ids):
        reg_ids = self.browse(cr, uid, ids)
        for reg_id in reg_ids:
            src = reg_id.event_id.reply_to or False
            dest = []
            if reg_id.email_from:
                dest += [reg_id.email_from]
            if reg_id.email_cc:
                dest += [reg_id.email_cc]
            if reg_id.event_id.mail_auto_confirm or reg_id.event_id.mail_auto_registr:
                if dest and src:
                    if reg_id.event_id.state in ['draft', 'fixed', 'open', 'confirm', 'running'] and reg_id.event_id.mail_auto_registr:
                        tools.email_send(src, dest, 'Auto Registration: '+'['+str(reg_id.id)+']'+' '+reg_id.name, reg_id.event_id.mail_registr, openobject_id = str(reg_id.id))
                    if (reg_id.event_id.state in ['confirm', 'running']) and reg_id.event_id.mail_auto_confirm:
                        tools.email_send(src, dest, 'Auto Confirmation: '+'['+str(reg_id.id)+']'+' '+reg_id.name, reg_id.event_id.mail_confirm, openobject_id = str(reg_id.id))
                if not src:
                    raise osv.except_osv(_('Error!'), _('You must define a reply-to address in order to mail the participant. You can do this in the Mailing tab of your event. Note that this is also the place where you can configure your event to not send emails automaticly while registering'))
        return False

    def _create_invoice_lines(self, cr, uid, ids, vals):
        return self.pool.get('account.invoice.line').create(cr, uid, vals)

    _name= 'event.registration'
    _description = 'Event Registration'
    _inherit = 'crm.meeting'

    _columns = {
        'email_cc': fields.text('Watchers Emails', size=252 , help="These \
people will receive a copy of the future communication between partner \
and users by email"),
        'nb_register': fields.integer('Number of Registration', readonly=True, states={'draft': [('readonly', False)]}), 
        'event_id': fields.many2one('event.event', 'Event Related', required=True), 
        "partner_invoice_id": fields.many2one('res.partner', 'Partner Invoiced'), 
        "contact_id": fields.many2one('res.partner.contact', 'Partner Contact'), #TODO: filter only the contacts that have a function into the selected partner_id
        "unit_price": fields.float('Unit Price'), 
        "badge_title": fields.char('Badge Title', size=128), 
        "badge_name": fields.char('Badge Name', size=128), 
        "badge_partner": fields.char('Badge Partner', size=128), 
        "invoice_label": fields.char("Label Invoice", size=128, required=True), 
        "tobe_invoiced": fields.boolean("To be Invoiced"), 
        "invoice_id": fields.many2one("account.invoice", "Invoice"), 
        'date_closed': fields.datetime('Closed', readonly=True), 
        'ref': fields.reference('Reference', selection=crm._links_get, size=128), 
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128), 
        'canal_id': fields.many2one('res.partner.canal', 'Channel', help="The channels represent the different communication modes available with the customer." \
                                                                        " With each commercial opportunity, you can indicate the canall which is this opportunity source."), 
        'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                       "the partner mentality in relation to our services.The scale has" \
                                                                       "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."), 
    }
    
    _defaults = {
        'nb_register': lambda *a: 1, 
        'tobe_invoiced': lambda *a: True, 
        'name': lambda *a: 'Registration', 
    }

    def onchange_badge_name(self, cr, uid, ids, badge_name):
        data ={}
        if not badge_name:
            return data
        data['name'] = 'Registration: ' + badge_name
        return {'value': data}

    def onchange_contact_id(self, cr, uid, ids, contact, partner):
        data ={}
        if not contact:
            return data
        contact_id = self.pool.get('res.partner.contact').browse(cr, uid, contact)
        data['badge_name'] = contact_id.name
        data['badge_title'] = contact_id.title
        if partner:
            partner_addresses = self.pool.get('res.partner.address').search(cr, uid, [('partner_id', '=', partner)])
            job_ids = self.pool.get('res.partner.job').search(cr, uid, [('contact_id', '=', contact), ('address_id', 'in', partner_addresses)])
            if job_ids:
                data['email_from'] = self.pool.get('res.partner.job').browse(cr, uid, job_ids[0]).email
        d = self.onchange_badge_name(cr, uid, ids, data['badge_name'])
        data.update(d['value'])

        return {'value': data}

    def onchange_event(self, cr, uid, ids, event_id, partner_invoice_id):
        context={}
        if not event_id:
            return {'value': {'unit_price': False , 'invoice_label': False }}
        data_event =  self.pool.get('event.event').browse(cr, uid, event_id)
        if data_event.product_id:
            if not partner_invoice_id:
                unit_price=self.pool.get('product.product').price_get(cr, uid, [data_event.product_id.id], context=context)[data_event.product_id.id]
                return {'value': {'unit_price': unit_price , 'invoice_label': data_event.product_id.name}}
            data_partner = self.pool.get('res.partner').browse(cr, uid, partner_invoice_id)
            context.update({'partner_id': data_partner})
            unit_price = self.pool.get('product.product')._product_price(cr, uid, [data_event.product_id.id], False, False, {'pricelist': data_partner.property_product_pricelist.id})[data_event.product_id.id]
            return {'value': {'unit_price': unit_price , 'invoice_label': data_event.product_id.name}}
        return {'value': {'unit_price': False, 'invoice_label': False}}


    def onchange_partner_id(self, cr, uid, ids, part, event_id, email=False):
        data={}
        data['badge_partner'] = data['contact_id'] = data['partner_invoice_id'] = data['email_from'] = data['badge_title'] = data['badge_name'] = False
        if not part:
            return {'value': data}
        data['partner_invoice_id']=part
        # this calls onchange_partner_invoice_id
        d = self.onchange_partner_invoice_id(cr, uid, ids, event_id, part)
        # this updates the dictionary
        data.update(d['value'])
        addr = self.pool.get('res.partner').address_get(cr, uid, [part])
        if addr:
            if addr.has_key('default'):
                job_ids = self.pool.get('res.partner.job').search(cr, uid, [('address_id', '=', addr['default'])])
                if job_ids:
                    data['contact_id'] = self.pool.get('res.partner.job').browse(cr, uid, job_ids[0]).contact_id.id
                    d = self.onchange_contact_id(cr, uid, ids, data['contact_id'], part)
                    data.update(d['value'])
        partner_data = self.pool.get('res.partner').browse(cr, uid, part)
        data['badge_partner'] = partner_data.name
        return {'value': data}

    def onchange_partner_invoice_id(self, cr, uid, ids, event_id, partner_invoice_id):
        data={}
        context={}
        data['unit_price']=False
        if not event_id:
            return {'value': data}
        data_event =  self.pool.get('event.event').browse(cr, uid, event_id)

        if data_event.product_id:
            if not partner_invoice_id:
                data['unit_price']=self.pool.get('product.product').price_get(cr, uid, [data_event.product_id.id], context=context)[data_event.product_id.id]
                return {'value': data}
            data_partner = self.pool.get('res.partner').browse(cr, uid, partner_invoice_id)
            context.update({'partner_id': data_partner})
            data['unit_price'] = self.pool.get('product.product')._product_price(cr, uid, [data_event.product_id.id], False, False, {'pricelist': data_partner.property_product_pricelist.id})[data_event.product_id.id]
            return {'value': data}
        return {'value': data}

    def onchange_categ_id(self, cr, uid, ids, categ, context={}):
        if not categ:
            return {'value': {}}
        cat = self.pool.get('crm.case.categ').browse(cr, uid, categ, context).probability
        return {'value': {'probability': cat}}

event_registration()



class report_event_registration(osv.osv):
    _name = "report.event.registration"
    _description = "Events on registrations"
    _auto = False
    _columns = {
        'name': fields.char('Event', size=20), 
        'date_begin': fields.datetime('Beginning date', required=True), 
        'date_end': fields.datetime('Ending date', required=True), 
        'draft_state': fields.integer('Draft Registration', size=20), 
        'confirm_state': fields.integer('Confirm Registration', size=20), 
        'register_max': fields.integer('Maximum Registrations'), 
    }
    def init(self, cr):
        cr.execute("""
            create or replace view report_event_registration as (
                select
                e.id as id,
                c.name as name,
                e.date_begin as date_begin,
                e.date_end as date_end,
                (SELECT sum(c.nb_register) FROM event_registration  c  WHERE c.section_id=e.section_id and state in ('draft')) as draft_state,
                (SELECT sum(c.nb_register) FROM event_registration  c  WHERE c.section_id=e.section_id and state in ('open')) as confirm_state,
                e.register_max as register_max
                from
                event_event e,crm_case_section c
                where
                e.section_id=c.id
                )""")

report_event_registration()

class report_event_type_registration(osv.osv):
    _name = "report.event.type.registration"
    _description = "Event type on registration"
    _auto = False
    _columns = {
        'name': fields.char('Event Type', size=20), 
        'nbevent': fields.integer('Number Of Events'), 
        'draft_state': fields.integer('Draft Registrations', size=20), 
        'confirm_state': fields.integer('Confirm Registrations', size=20), 
        }
        
        
    def init(self, cr):
        cr.execute("""
            create or replace view report_event_type_registration as (
                select
                count(t.id) as id,
                t.name as name,
                (select sum(c.nb_register) from event_registration c, event_event e  where c.section_id=e.section_id and c.state='draft' and e.type=t.id ) as draft_state ,
                (select sum(c.nb_register) from event_registration c, event_event e  where c.section_id=e.section_id and c.state='open' and e.type=t.id ) as  confirm_state,
                count(t.id) as nbevent
                from
                    event_event e
                inner join
                    crm_case_section c1 on (e.section_id=c1.id)
                inner join
                    event_type t on (e.type=t.id)
                group by
                    t.name,t.id

            )""")
report_event_type_registration()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

