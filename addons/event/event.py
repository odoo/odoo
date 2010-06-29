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

from crm import crm
from osv import fields, osv
from tools.translate import _
import netsvc
import pooler
import time
import tools


class event_type(osv.osv):    
    """ Event Type """    
    _name = 'event.type'
    _description = __doc__
    _columns = {
        'name': fields.char('Event type', size=64, required=True), 
    }
    
event_type()

class event_event(osv.osv):    
    """Event"""    
    _name = 'event.event'
    _description = __doc__
    _inherit = 'crm.case.section'
    _order = 'date_begin'

    def copy(self, cr, uid, id, default=None, context=None):        
        """ Copy record of Given id       
        @param id: Id of Event Registration type record.
        @param context: A standard dictionary for contextual values
        """
        if not default:
            default = {}
        default.update({
            'code': self.pool.get('ir.sequence').get(cr, uid, 'event.event'), 
            'state': 'draft'
        })    
        return super(event_event, self).copy(cr, uid, id, default=default, context=context)

    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def button_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def button_confirm(self, cr, uid, ids, context=None):
        register_pool = self.pool.get('event.registration')
        for event in self.browse(cr, uid, ids, context=context):
            if event.mail_auto_confirm:
                #send reminder that will confirm the event for all the people that were already confirmed
                reg_ids = register_pool.search(cr, uid, [
                               ('event_id', '=', event.id), 
                               ('state', 'not in', ['draft', 'cancel'])])
                register_pool.mail_user_confirm(cr, uid, reg_ids)
                    
        return self.write(cr, uid, ids, {'state': 'confirm'})


    def _get_register(self, cr, uid, ids, fields, args, context=None):        
        """
        Get Confirm or uncofirm register value.       
        @param ids: List of Event registration type's id
        @param fields: List of function fields(register_current and register_prospect).
        @param context: A standard dictionary for contextual values
        @return: Dictionary of function fields value. 
        """
        register_pool = self.pool.get('event.registration')
        res = {}
        for event in self.browse(cr, uid, ids, context):
            res[event.id] = {}
            for field in fields:
                res[event.id][field] = False
            state = []
            if 'register_current' in fields:
                state.append('open')
            if 'register_prospect' in fields: 
                state.append('draft')
            
            reg_ids = register_pool.search(cr, uid, [
                       ('event_id', '=', event.id), 
                       ('state', 'in', state)])
            if 'register_current' in fields:
                res[event.id]['register_current'] = len(reg_ids)
            if 'register_prospect' in fields: 
                res[event.id]['register_prospect'] = len(reg_ids)
            
               
        return res

    def write(self, cr, uid, ids, vals, context=None):
        """
        Writes values in one or several fields.
        @param ids: List of Event registration type's IDs
        @param vals: dictionary with values to update.
        @return: True
        """
        register_pool = self.pool.get('event.registration')
        res = super(event_event, self).write(cr, uid, ids, vals, context=context)
        if vals.get('date_begin', False) or vals.get('mail_auto_confirm', False) or vals.get('mail_confirm', False):
            for event in self.browse(cr, uid, ids, context=context):
                #change the deadlines of the registration linked to this event
                register_values = {}
                if vals.get('date_begin', False):
                    register_values['date_deadline'] = vals['date_begin']

                #change the description of the registration linked to this event
                if vals.get('mail_auto_confirm', False):
                    if vals['mail_auto_confirm']:
                        if 'mail_confirm' not in vals:
                            vals['mail_confirm'] = event.mail_confirm
                    else:
                        vals['mail_confirm'] = False
                if 'mail_confirm' in vals:
                    register_values['description'] = vals['mail_confirm']

                if register_values:
                    reg_ids = register_pool.search(cr, uid, [('event_id', '=', event.id)])
                    register_pool.write(cr, uid, reg_ids, register_values)
        return res

    _columns = {
        'type': fields.many2one('event.type', 'Type', help="Type of Event like Seminar, Exhibition, Conference, Training."), 
        'register_max': fields.integer('Maximum Registrations', help="Provide Maximun Number of Registrations"), 
        'register_min': fields.integer('Minimum Registrations', help="Providee Minimum Number of Registrations"), 
        'register_current': fields.function(_get_register, method=True, string='Confirmed Registrations', multi='register_current', help="Total of Open Registrations"), 
        'register_prospect': fields.function(_get_register, method=True, string='Unconfirmed Registrations', multi='register_prospect', help="Total of Prospect Registrations"), 
        'date_begin': fields.datetime('Beginning date', required=True, help="Beginning Date of Event"), 
        'date_end': fields.datetime('Closing date', required=True, help="Closing Date of Event"), 
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, required=True, help='If event is created, the state is \'Draft\'.\n If event is confirmed for the particular dates the state is set to \'Confirmed\'.\
                                  \nIf the event is over, the state is set to \'Done\'.\n If event is cancelled the state is set to \'Cancelled\'.'), 
        'mail_auto_registr': fields.boolean('Mail Auto Register', help='Check this box if you want to use the automatic mailing for new registration'), 
        'mail_auto_confirm': fields.boolean('Mail Auto Confirm', help='Check this box if you want ot use the automatic confirmation emailing or the reminder'), 
        'mail_registr': fields.text('Registration Email', help='This email will be sent when someone subscribes to the event.'), 
        'mail_confirm': fields.text('Confirmation Email', help="This email will be sent when the event gets confimed or when someone subscribes to a confirmed event. This is also the email sent to remind someone about the event."), 
        'product_id': fields.many2one('product.product', 'Product', required=True, help="Product which is provided cost of event. Invoice of event will be created with this Product."),
        'note': fields.text('Notes', help="Description or Summary of Event")
    }

    _defaults = {
        'state': 'draft', 
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'event.event'), 
        'user_id': lambda obj, cr, uid, context: uid, 
    }

event_event()

class event_registration(osv.osv):    
    """Event Registration"""   

    _name= 'event.registration'
    _description = __doc__
    _inherit = 'crm.meeting'

    _columns = {
        'email_cc': fields.text('CC', size=252 , help="These \
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
        "event_product": fields.char("Product Name", size=128, required=True), 
        "tobe_invoiced": fields.boolean("To be Invoiced"), 
        "invoice_id": fields.many2one("account.invoice", "Invoice"), 
        'date_closed': fields.datetime('Closed', readonly=True), 
        'ref': fields.reference('Reference', selection=crm._links_get, size=128), 
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128), 
    }
    
    _defaults = {
        'nb_register': 1, 
        'tobe_invoiced':  True, 
        'name': 'Registration', 
    }

    def _make_invoice(self, cr, uid, reg, lines, context=None):
        """ Create Invoice from Invoice lines
        @param reg : Object of event.registration
        @param lines: ids of Invoice lines 
        """
        if context is None:
            context = {}
        inv_pool = self.pool.get('account.invoice')
        inv_lines_pool = self.pool.get('account.invoice.line')
        
        val_invoice = inv_pool.onchange_partner_id(cr, uid, [], 'out_invoice', reg.partner_invoice_id.id, False, False)            
        val_invoice['value'].update({'partner_id': reg.partner_invoice_id.id})
        partner_address_id = val_invoice['value']['address_invoice_id']

        value = inv_lines_pool.product_id_change(cr, uid, [], reg.event_id.product_id.id, uom =False, partner_id=reg.partner_invoice_id.id, fposition_id=reg.partner_invoice_id.property_account_position.id)
        
        l = inv_lines_pool.read(cr, uid, lines)
        
        val_invoice['value'].update({
                'origin': reg.event_product, 
                'reference': False, 
                'invoice_line': [(6, 0, lines)], 
                'comment': "", 
            })
        inv_id = inv_pool.create(cr, uid, val_invoice['value'])   
        inv_pool.button_compute(cr, uid, [inv_id])
        self._history(cr, uid, [reg], _('Invoiced'))
        return inv_id

    def action_invoice_create(self, cr, uid, ids, grouped=False, date_inv = False, context=None):
        """ Action of Create Invoice """
        res = False
        invoices = {}
        tax_ids=[]
        
        inv_lines_pool = self.pool.get('account.invoice.line')
        inv_pool = self.pool.get('account.invoice')
        product_pool = self.pool.get('product.product')
        contact_pool = self.pool.get('res.partner.contact')
        if not context:
            context = {}
        # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        if date_inv:
            context['date_inv'] = date_inv

        for reg in self.browse(cr, uid, ids, context=context):
            
            val_invoice = inv_pool.onchange_partner_id(cr, uid, [], 'out_invoice', reg.partner_invoice_id.id, False, False)
            
            val_invoice['value'].update({'partner_id': reg.partner_invoice_id.id})
            partner_address_id = val_invoice['value']['address_invoice_id']
                
            if not partner_address_id:
               raise osv.except_osv(_('Error !'),
                        _("Registered partner doesn't have an address to make the invoice."))
                                
            value = inv_lines_pool.product_id_change(cr, uid, [], reg.event_id.product_id.id, uom =False, partner_id=reg.partner_invoice_id.id, fposition_id=reg.partner_invoice_id.property_account_position.id)
            product = product_pool.browse(cr, uid, reg.event_id.product_id.id, context=context)
            for tax in product.taxes_id:
                tax_ids.append(tax.id)

            vals = value['value']
            c_name = reg.contact_id and ('-' + contact_pool.name_get(cr, uid, [reg.contact_id.id])[0][1]) or ''
            vals.update({
                'name': reg.event_product + '-' + c_name, 
                'price_unit': reg.unit_price, 
                'quantity': reg.nb_register, 
                'product_id':reg.event_id.product_id.id, 
                'invoice_line_tax_id': [(6, 0, tax_ids)], 
            })
            inv_line_ids = self._create_invoice_lines(cr, uid, [reg.id], vals)
            invoices.setdefault(reg.partner_id.id, []).append((reg, inv_line_ids))
           
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], [v for k , v in val], context=context)
                
                for k , v in val:
                    self.write(cr, uid, [k.id], {'state': 'done', 'invoice_id': res}, context=context)
                    
            else:
               for k , v in val:
                   res = self._make_invoice(cr, uid, k, [v], context=context)
                   self.write(cr, uid, [k.id], {'state': 'done', 'invoice_id': res}, context=context)
        return res

    def check_confirm(self, cr, uid, ids, context=None):
        """
        Check confirm event register on given id.
        @param ids: List of Event registration's IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value which open Confirm registration form.
        """
        data_pool = self.pool.get('ir.model.data')
        unconfirmed_ids = []
        for registration in self.browse(cr, uid, ids, context=context):
            total_confirmed = registration.event_id.register_current + registration.nb_register
            if total_confirmed <= registration.event_id.register_max or registration.event_id.register_max == 0:
                self.write(cr, uid, [registration.id], {'state': 'open'}, context=context)
                self.mail_user(cr, uid, [registration.id])           
                self._history(cr, uid, [registration.id], _('Open')) 
            else:
                unconfirmed_ids.append(registration.id)
        if unconfirmed_ids:
            view_id = data_pool._get_id(cr, uid, 'event', 'view_event_confirm_registration')
            view_data = data_pool.browse(cr, uid, view_id)
            view_id = view_data.res_id
            context['registration_ids'] = unconfirmed_ids
            return {
                'name': _('Confirm Registration'), 
                'context': context, 
                'view_type': 'form', 
                'view_mode': 'tree,form', 
                'res_model': 'event.confirm.registration', 
                'views': [(view_id, 'form')],                     
                'type': 'ir.actions.act_window', 
                'target': 'new', 
                'context': context,
                'nodestroy': True
            }
        return True    

    def button_reg_close(self, cr, uid, ids, *args):        
        registrations = self.browse(cr, uid, ids) 
        self._history(cr, uid, registrations, _('Done'))
        self.write(cr, uid, ids, {'state': 'done', 'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True
    
    def button_reg_cancel(self, cr, uid, ids, *args):        
        registrations = self.browse(cr, uid, ids)
        self._history(cr, uid, registrations, _('Cancel'))
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    def create(self, cr, uid, values, context=None):
        """ Overrides orm create method.
        """
        event = self.pool.get('event.event').browse(cr, uid, values['event_id'], context=context)
        
        values['date_deadline']= event.date_begin
        values['description']= event.mail_confirm
        res = super(event_registration, self).create(cr, uid, values, context=context)
        registrations = self.browse(cr, uid, [res], context=context)
        self._history(cr, uid, registrations, _('Created'))
        return res

    def write(self, cr, uid, ids, values, context=None):    
        if 'event_id' in values:
            event = self.pool.get('event.event').browse(cr, uid, values['event_id'], context=context)
            values['date_deadline']= event.date_begin
            values['description']= event.mail_confirm
        return super(event_registration, self).write(cr, uid, ids, values, context=context)
    

    def mail_user(self, cr, uid, ids, confirm=False, context=None):
        """
        Send email to user 
        """
        if not context:
            context = {}
        
        for reg_id in self.browse(cr, uid, ids):
            src = reg_id.event_id.reply_to or False
            dest = []
            if reg_id.email_from:
                dest += [reg_id.email_from]
            if reg_id.email_cc:
                dest += [reg_id.email_cc]
            if dest and src:
                if confirm:
                   tools.email_send(src, dest, 
                        _('Auto Confirmation: [%s] %s') %(reg_id.id, reg_id.name),
                        reg_id.event_id.mail_confirm, 
                        openobject_id = reg_id.id)
                elif reg_id.event_id.mail_auto_confirm or reg_id.event_id.mail_auto_registr:
                    if reg_id.event_id.state in ['draft', 'fixed', 'open', 'confirm', 'running'] and reg_id.event_id.mail_auto_registr:
                        tools.email_send(src, dest, 
                            _('Auto Registration: [%s] %s') %(reg_id.id, reg_id.name),
                             reg_id.event_id.mail_registr, openobject_id = reg_id.id)
                    if (reg_id.event_id.state in ['confirm', 'running']) and reg_id.event_id.mail_auto_confirm:
                        tools.email_send(src, dest, 
                            _('Auto Confirmation: [%s] %s') %(reg_id.id, reg_id.name), 
                            reg_id.event_id.mail_confirm, openobject_id = reg_id.id)
                    
            if not src:
                raise osv.except_osv(_('Error!'), _('You must define a reply-to address in order to mail the participant. You can do this in the Mailing tab of your event. Note that this is also the place where you can configure your event to not send emails automaticly while registering'))

        return True

    def mail_user_confirm(self, cr, uid, ids, context=None):
        """
        Send email to user 
        """
        return self.mail_user(cr, uid, ids, confirm=True, context=context)

    def _create_invoice_lines(self, cr, uid, ids, vals):
        """ Create account Invoice line for Registration Id.
        """
        return self.pool.get('account.invoice.line').create(cr, uid, vals)

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
            return {'value': {'unit_price': False, 'event_product': False}}
        data_event =  self.pool.get('event.event').browse(cr, uid, event_id)
        
        if data_event.product_id:
            if not partner_invoice_id:
                unit_price=self.pool.get('product.product').price_get(cr, uid, [data_event.product_id.id], context=context)[data_event.product_id.id]
                return {'value': {'unit_price': unit_price, 'event_product': data_event.product_id.name}}
            data_partner = self.pool.get('res.partner').browse(cr, uid, partner_invoice_id)
            context.update({'partner_id': data_partner})
            unit_price = self.pool.get('product.product')._product_price(cr, uid, [data_event.product_id.id], False, False, {'pricelist': data_partner.property_product_pricelist.id})[data_event.product_id.id]
            return {'value': {'unit_price': unit_price, 'event_product': data_event.product_id.name}}
        
        return {'value': {'unit_price': False, 'event_product': False}}

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

event_registration()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

