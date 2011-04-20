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

import time

from crm import crm
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
from crm import wizard

wizard.email_compose_message.email_model.append('event.registration')

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
    _order = 'date_begin'

    def copy(self, cr, uid, id, default=None, context=None):
        """ Copy record of Given id
        @param id: Id of Event record.
        @param context: A standard dictionary for contextual values
        """
        if not default:
            default = {}
        default.update({
            'state': 'draft',
            'registration_ids': False,
        })
        return super(event_event, self).copy(cr, uid, id, default=default, context=context)

    def onchange_product(self, cr, uid, ids, product_id=False):
        """This function returns value of  product's unit price based on product id.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Event IDs
        @param product_id: Product's id
        """
        if not product_id:
            return {'value': {'unit_price': False}}
        else:
           unit_price=self.pool.get('product.product').price_get(cr, uid, [product_id])[product_id]
           return {'value': {'unit_price': unit_price}}

    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def button_done(self, cr, uid, ids, context=None):
        if type(ids) in (int, long,):
            ids = [ids]
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def do_confirm(self, cr, uid, ids, context=None):
        """ Confirm Event and send confirmation email to all register peoples
        """
        register_pool = self.pool.get('event.registration')
        for event in self.browse(cr, uid, ids, context=context):
            if event.mail_auto_confirm:
                #send reminder that will confirm the event for all the people that were already confirmed
                reg_ids = register_pool.search(cr, uid, [
                               ('event_id', '=', event.id),
                               ('state', 'not in', ['draft', 'cancel'])], context=context)
                register_pool.mail_user_confirm(cr, uid, reg_ids)

        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def button_confirm(self, cr, uid, ids, context=None):
        """This Function Confirm Event.
        @param ids: List of Event IDs
        @param context: A standard dictionary for contextual values
        @return: True
        """
        if context is None:
            context = {}
        res = False
        if type(ids) in (int, long,):
            ids = [ids]
        data_pool = self.pool.get('ir.model.data')
        unconfirmed_ids = []
        for event in self.browse(cr, uid, ids, context=context):
            total_confirmed = event.register_current
            if total_confirmed >= event.register_min or event.register_max == 0:
                res = self.do_confirm(cr, uid, [event.id], context=context)
            else:
                unconfirmed_ids.append(event.id)
        if unconfirmed_ids:
            view_id = data_pool.get_object_reference(cr, uid, 'event', 'view_event_confirm')
            view_id = view_id and view_id[1] or False
            context['event_ids'] = unconfirmed_ids
            return {
                'name': _('Confirm Event'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'event.confirm',
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context,
                'nodestroy': True
            }
        return res

    def _get_register(self, cr, uid, ids, fields, args, context=None):
        """Get Confirm or uncofirm register value.
        @param ids: List of Event registration type's id
        @param fields: List of function fields(register_current and register_prospect).
        @param context: A standard dictionary for contextual values
        @return: Dictionary of function fields value.
        """
        register_pool = self.pool.get('event.registration')
        res = {}
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = {}
            for field in fields:
                res[event.id][field] = False
            state = []
            if 'register_current' in fields:
                state += ['open', 'done']
            if 'register_prospect' in fields:
                state.append('draft')

            reg_ids = register_pool.search(cr, uid, [
                        ('event_id', '=', event.id),
                       ('state', 'in', state)], context=context)

            number = 0.0
            if reg_ids:
                cr.execute('SELECT SUM(nb_register) FROM event_registration WHERE id IN %s', (tuple(reg_ids),))
                number = cr.fetchone()

            if 'register_current' in fields:
                res[event.id]['register_current'] = number and number[0] or 0.0
            if 'register_prospect' in fields:
                res[event.id]['register_prospect'] = number and number[0] or 0.0
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
                    reg_ids = register_pool.search(cr, uid, [('event_id', '=', event.id)], context=context)
                    register_pool.write(cr, uid, reg_ids, register_values, context=context)
        return res

    _columns = {
        'name': fields.char('Summary', size=64, required=True, translate=True, readonly=False, states={'done': [('readonly', True)]}),
        'user_id': fields.many2one('res.users', 'Responsible User', readonly=False, states={'done': [('readonly', True)]}),
        'parent_id': fields.many2one('event.event', 'Parent Event', readonly=False, states={'done': [('readonly', True)]}),
        'section_id': fields.many2one('crm.case.section', 'Sale Team', readonly=False, states={'done': [('readonly', True)]}),
        'child_ids': fields.one2many('event.event', 'parent_id', 'Child Events', readonly=False, states={'done': [('readonly', True)]}),
        'reply_to': fields.char('Reply-To', size=64, readonly=False, states={'done': [('readonly', True)]}, help="The email address put in the 'Reply-To' of all emails sent by OpenERP"),
        'type': fields.many2one('event.type', 'Type', help="Type of Event like Seminar, Exhibition, Conference, Training.", readonly=False, states={'done': [('readonly', True)]}),
        'register_max': fields.integer('Maximum Registrations', help="Provide Maximun Number of Registrations", readonly=True, states={'draft': [('readonly', False)]}),
        'register_min': fields.integer('Minimum Registrations', help="Providee Minimum Number of Registrations", readonly=True, states={'draft': [('readonly', False)]}),
        'register_current': fields.function(_get_register, method=True, string='Confirmed Registrations', multi='register_current',
            help="Total of Open and Done Registrations"),
        'register_prospect': fields.function(_get_register, method=True, string='Unconfirmed Registrations', multi='register_prospect',
            help="Total of Prospect Registrati./event/event.py:41:ons"),
        'registration_ids': fields.one2many('event.registration', 'event_id', 'Registrations', readonly=False, states={'done': [('readonly', True)]}),
        'date_begin': fields.datetime('Beginning date', required=True, help="Beginning Date of Event", readonly=True, states={'draft': [('readonly', False)]}),
        'date_end': fields.datetime('Closing date', required=True, help="Closing Date of Event", readonly=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('done', 'Done'),
            ('cancel', 'Cancelled')],
            'State', readonly=True, required=True,
            help='If event is created, the state is \'Draft\'.If event is confirmed for the particular dates the state is set to \'Confirmed\'. If the event is over, the state is set to \'Done\'.If event is cancelled the state is set to \'Cancelled\'.'),
        'mail_auto_registr': fields.boolean('Mail Auto Register', readonly=False, states={'done': [('readonly', True)]}, help='Check this box if you want to use the automatic mailing for new registration'),
        'mail_auto_confirm': fields.boolean('Mail Auto Confirm', readonly=False, states={'done': [('readonly', True)]}, help='Check this box if you want ot use the automatic confirmation emailing or the reminder'),
        'mail_registr': fields.text('Registration Email', readonly=False, states={'done': [('readonly', True)]}, help='This email will be sent when someone subscribes to the event.'),
        'mail_confirm': fields.text('Confirmation Email', readonly=False, states={'done': [('readonly', True)]}, help="This email will be sent when the event gets confimed or when someone subscribes to a confirmed event. This is also the email sent to remind someone about the event."),
        'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="The invoices of this event registration will be created with this Product. Thus it allows you to set the default label and the accounting info you want by default on these invoices."),
        'note': fields.text('Notes', help="Description or Summary of Event", readonly=False, states={'done': [('readonly', True)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', readonly=True, states={'draft': [('readonly', False)]}, help="Pricelist version for current event."),
        'unit_price': fields.related('product_id', 'list_price', type='float', string='Registration Cost', readonly=True, states={'draft':[('readonly',False)]}, help="This will be the default price used as registration cost when invoicing this event. Note that you can specify for each registration a specific amount if you want to", digits_compute=dp.get_precision('Sale Price')),
        'main_speaker_id': fields.many2one('res.partner','Main Speaker', readonly=False, states={'done': [('readonly', True)]}, help="Speaker who are giving speech on event."),
        'speaker_ids': fields.many2many('res.partner', 'event_speaker_rel', 'speaker_id', 'partner_id', 'Other Speakers', readonly=False, states={'done': [('readonly', True)]}),
        'address_id': fields.many2one('res.partner.address','Location Address', readonly=False, states={'done': [('readonly', True)]}),
        'speaker_confirmed': fields.boolean('Speaker Confirmed', readonly=False, states={'done': [('readonly', True)]}),
        'country_id': fields.related('address_id', 'country_id',
                    type='many2one', relation='res.country', string='Country', readonly=False, states={'done': [('readonly', True)]}),
        'language': fields.char('Language',size=64, readonly=False, states={'done': [('readonly', True)]}),
        'note': fields.text('Description', readonly=False, states={'done': [('readonly', True)]}),
        'company_id': fields.many2one('res.company', 'Company', required=False, change_default=True, readonly=False, states={'done': [('readonly', True)]}),
    }

    _defaults = {
        'state': 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'event.event', context=c),
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        return super(event_event, self)._check_recursion(cr, uid, ids, context=context)

    def _check_closing_date(self, cr, uid, ids, context=None):
        for event in self.browse(cr, uid, ids, context=context):
            if event.date_end < event.date_begin:
                return False
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive event.', ['parent_id']),
        (_check_closing_date, 'Error ! Closing Date cannot be set before Beginning Date.', ['date_end']),
    ]

    def do_team_change(self, cr, uid, ids, team_id, context=None):
        """
        On Change Callback: when team change, this is call.
        on this function, take value of reply_to from selected team.
        """
        if not team_id:
            return {}
        team_pool = self.pool.get('crm.case.section')
        res = {}
        team = team_pool.browse(cr, uid, team_id, context=context)
        if team.reply_to:
            res = {'value': {'reply_to': team.reply_to}}
        return res

event_event()

class event_registration(osv.osv):
    """Event Registration"""
    _name= 'event.registration'
    _description = __doc__
    _inherit = 'email.thread'

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.unit_price * line.nb_register
            pricelist = line.event_id.pricelist_id or line.partner_invoice_id.property_product_pricelist
            cur = pricelist and pricelist.currency_id or False
            res[line.id] = cur and cur_obj.round(cr, uid, cur, price) or price
        return res

    _columns = {
        'name': fields.char('Summary', size=124,  readonly=True, states={'draft': [('readonly', False)]}),
        'email_cc': fields.text('CC', size=252, readonly=False, states={'done': [('readonly', True)]}, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'nb_register': fields.integer('Quantity', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="Number of Registrations or Tickets"),
        'event_id': fields.many2one('event.event', 'Event', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done': [('readonly', True)]}),
        "partner_invoice_id": fields.many2one('res.partner', 'Partner Invoiced', readonly=True, states={'draft': [('readonly', False)]}),
        "contact_id": fields.many2one('res.partner.contact', 'Partner Contact', readonly=False, states={'done': [('readonly', True)]}), #TODO: filter only the contacts that have a function into the selected partner_id
        "unit_price": fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Sale Price'), readonly=True, states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal', digits_compute=dp.get_precision('Sale Price'), store=True),
        "badge_ids": fields.one2many('event.registration.badge', 'registration_id', 'Badges', readonly=False, states={'done': [('readonly', True)]}),
        "event_product": fields.char("Invoice Name", size=128, readonly=True, states={'draft': [('readonly', False)]}),
        "tobe_invoiced": fields.boolean("To be Invoiced", readonly=True, states={'draft': [('readonly', False)]}),
        "invoice_id": fields.many2one("account.invoice", "Invoice", readonly=True),
        'date_closed': fields.datetime('Closed', readonly=True),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'email_from': fields.char('Email', size=128, states={'done': [('readonly', True)]}, help="These people will receive email."),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_date': fields.datetime('Write Date', readonly=True),
        'description': fields.text('Description', states={'done': [('readonly', True)]}),
        'message_ids': fields.one2many('email.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        'log_ids': fields.one2many('email.message', 'res_id', 'Logs', domain=[('history', '=', False),('model','=',_name)]),
        'date_deadline': fields.related('event_id','date_end', type='datetime', string="End Date", readonly=True),
        'date': fields.related('event_id', 'date_begin', type='datetime', string="Start Date", readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible', states={'done': [('readonly', True)]}),
        'active': fields.boolean('Active'),
        'section_id': fields.related('event_id', 'section_id', type='many2one', relation='crm.case.section', string='Sale Team', store=True, readonly=True),
        'company_id': fields.related('event_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('open', 'Confirmed'),
                                    ('draft', 'Unconfirmed'),
                                    ('cancel', 'Cancelled'),
                                    ('done', 'Done')], 'State', \
                                    size=16, readonly=True)
    }
    _defaults = {
        'nb_register': 1,
        'tobe_invoiced':  True,
        'state': 'draft',
        'active': 1,
        'user_id': lambda self, cr, uid, ctx: uid,
    }

    def _make_invoice(self, cr, uid, reg, lines, context=None):
        """ Create Invoice from Invoice lines
        @param reg: Model of Event Registration
        @param lines: Ids of Invoice lines
        """
        if context is None:
            context = {}
        inv_pool = self.pool.get('account.invoice')
        val_invoice = inv_pool.onchange_partner_id(cr, uid, [], 'out_invoice', reg.partner_invoice_id.id, False, False)
        val_invoice['value'].update({'partner_id': reg.partner_invoice_id.id})
        val_invoice['value'].update({
                'origin': reg.event_product,
                'reference': False,
                'invoice_line': [(6, 0, lines)],
                'comment': "",
                'date_invoice': context.get('date_inv', False)
            })
        inv_id = inv_pool.create(cr, uid, val_invoice['value'], context=context)
        inv_pool.button_compute(cr, uid, [inv_id])
        self.history(cr, uid, [reg], _('Invoiced'))
        return inv_id

    def copy(self, cr, uid, id, default=None, context=None):
        """ Copy record of Given id
        @param id: Id of Registration record.
        @param context: A standard dictionary for contextual values
        """
        if not default:
            default = {}
        default.update({
            'invoice_id': False,
        })
        return super(event_registration, self).copy(cr, uid, id, default=default, context=context)

    def action_invoice_create(self, cr, uid, ids, grouped=False, date_inv = False, context=None):
        """ Action of Create Invoice """
        res = False
        invoices = {}
        tax_ids=[]
        new_invoice_ids = []
        inv_lines_pool = self.pool.get('account.invoice.line')
        inv_pool = self.pool.get('account.invoice')
        product_pool = self.pool.get('product.product')
        contact_pool = self.pool.get('res.partner.contact')
        if context is None:
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
            res = False
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], [v for k, v in val], context=context)

                for k, v in val:
                    self.do_close(cr, uid, [k.id], context={'invoice_id': res})

            else:
               for k, v in val:
                   res = self._make_invoice(cr, uid, k, [v], context=context)
                   self.do_close(cr, uid, [k.id], context={'invoice_id': res})
            if res: new_invoice_ids.append(res)
        return new_invoice_ids

    def do_open(self, cr, uid, ids, context=None):
        """ Open Registration
        """
        res = self.write(cr, uid, ids, {'state': 'open'}, context=context)
        self.mail_user(cr, uid, ids)
        self.history(cr, uid, ids, _('Open'))
        return res

    def do_close(self, cr, uid, ids, context=None):
        """ Close Registration
        """
        if context is None:
            context = {}
        invoice_id = context.get('invoice_id', False)
        values = {'state': 'done', 'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')}
        msg = _('Done')
        if invoice_id:
            values['invoice_id'] = invoice_id
        res = self.write(cr, uid, ids, values)
        self.history(cr, uid, ids, msg)
        return res

    def check_confirm(self, cr, uid, ids, context=None):
        """This Function Open Event Registration and send email to user.
        @param ids: List of Event registration's IDs
        @param context: A standard dictionary for contextual values
        @return: True
        """
        if type(ids) in (int, long,):
            ids = [ids]
        data_pool = self.pool.get('ir.model.data')
        unconfirmed_ids = []
        if context is None:
            context = {}
        for registration in self.browse(cr, uid, ids, context=context):
            total_confirmed = registration.event_id.register_current + registration.nb_register
            if total_confirmed <= registration.event_id.register_max or registration.event_id.register_max == 0:
                self.do_open(cr, uid, [registration.id], context=context)
            else:
                unconfirmed_ids.append(registration.id)
        if unconfirmed_ids:
            view_id = data_pool.get_object_reference(cr, uid, 'event', 'view_event_confirm_registration')
            view_id = view_id and view_id[1] or False
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

    def button_reg_close(self, cr, uid, ids, context=None):
        """This Function Close Event Registration.
        """
        data_pool = self.pool.get('ir.model.data')
        unclosed_ids = []
        for registration in self.browse(cr, uid, ids, context=context):
            if registration.tobe_invoiced and not registration.invoice_id:
                unclosed_ids.append(registration.id)
            else:
                self.do_close(cr, uid, [registration.id], context=context)
        if unclosed_ids:
            view_id = data_pool.get_object_reference(cr, uid, 'event', 'view_event_make_invoice')
            view_id = view_id and view_id[1] or False
            context['active_ids'] = unclosed_ids
            return {
                'name': _('Close Registration'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'event.make.invoice',
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context,
                'nodestroy': True
            }
        return True

    def button_reg_cancel(self, cr, uid, ids, *args):
        """This Function Cancel Event Registration.
        """
        registrations = self.browse(cr, uid, ids)
        self.history(cr, uid, registrations, _('Cancel'))
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def mail_user(self, cr, uid, ids, confirm=False, context=None):
        """
        Send email to user
        """
        email_message_obj = self.pool.get('email.message')
        for regestration in self.browse(cr, uid, ids, context=context):
            src = regestration.event_id.reply_to or False
            email_to = []
            email_cc = []
            if regestration.email_from:
                email_to = regestration.email_from
            if regestration.email_cc:
                email_cc += [regestration.email_cc]
            if not (email_to or email_cc):
                continue
            subject = ""
            body = ""
            if confirm:
                subject = _('Auto Confirmation: [%s] %s') %(regestration.id, regestration.name)
                body = regestration.event_id.mail_confirm
            elif regestration.event_id.mail_auto_confirm or regestration.event_id.mail_auto_registr:
                if regestration.event_id.state in ['draft', 'fixed', 'open', 'confirm', 'running'] and regestration.event_id.mail_auto_registr:
                    subject = _('Auto Registration: [%s] %s') %(regestration.id, regestration.name)
                    body = regestration.event_id.mail_registr
                if (regestration.event_id.state in ['confirm', 'running']) and regestration.event_id.mail_auto_confirm:
                    subject = _('Auto Confirmation: [%s] %s') %(regestration.id, regestration.name)
                    body = regestration.event_id.mail_confirm
            if subject or body:
                email_message_obj.schedule_with_attach(cr, uid, src, email_to, subject, body, model='event.registration', email_cc=email_cc, openobject_id=regestration.id)

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

    def onchange_contact_id(self, cr, uid, ids, contact, partner):

        """This function returns value of Badge Name, Badge Title based on Partner contact.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Registration IDs
        @param contact: Patner Contact IDS
        @param partner: Partner IDS
        """
        data ={}
        if not contact:
            return data
        addr_obj = self.pool.get('res.partner.address')
        job_obj = self.pool.get('res.partner.job')

        if partner:
            partner_addresses = addr_obj.search(cr, uid, [('partner_id', '=', partner)])
            job_ids = job_obj.search(cr, uid, [('contact_id', '=', contact), ('address_id', 'in', partner_addresses)])
            if job_ids:
                data['email_from'] = job_obj.browse(cr, uid, job_ids[0]).email
        return {'value': data}

    def onchange_event(self, cr, uid, ids, event_id, partner_invoice_id):
        """This function returns value of Product Name, Unit Price based on Event.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Registration IDs
        @param event_id: Event ID
        @param partner_invoice_id: Partner Invoice ID
        """
        context = {}
        if not event_id:
            return {'value': {'unit_price': False, 'event_product': False}}

        event_obj = self.pool.get('event.event')
        prod_obj = self.pool.get('product.product')
        res_obj = self.pool.get('res.partner')

        data_event =  event_obj.browse(cr, uid, event_id)
        res = {'value': {'unit_price': False,
                         'event_product': False,
                         'user_id': False,
                         'date': data_event.date_begin,
                         'date_deadline': data_event.date_end,
                         'description': data_event.note,
                         'name': data_event.name,
                         'section_id': data_event.section_id and data_event.section_id.id or False,
                        }}
        if data_event.user_id.id:
            res['value'].update({'user_id': data_event.user_id.id})
        if data_event.product_id:
            pricelist_id = data_event.pricelist_id and data_event.pricelist_id.id or False
            if partner_invoice_id:
                partner = res_obj.browse(cr, uid, partner_invoice_id, context=context)
                pricelist_id = pricelist_id or partner.property_product_pricelist.id
            unit_price = prod_obj._product_price(cr, uid, [data_event.product_id.id], False, False, {'pricelist': pricelist_id})[data_event.product_id.id]
            if not unit_price:
                unit_price = data_event.unit_price
            res['value'].update({'unit_price': unit_price, 'event_product': data_event.product_id.name})
        return res

    def onchange_partner_id(self, cr, uid, ids, part, event_id, email=False):
        """This function returns value of Patner Invoice id, Unit Price, badget title based on partner and Event.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Registration IDs
        @param event_id: Event ID
        @param partner_invoice_id: Partner Invoice ID
        """
        job_obj = self.pool.get('res.partner.job')
        res_obj = self.pool.get('res.partner')

        data = {}
        data['contact_id'], data['partner_invoice_id'], data['email_from'] = (False, False, False)
        if not part:
            return {'value': data}
        data['partner_invoice_id'] = part
        # this calls onchange_partner_invoice_id
        d = self.onchange_partner_invoice_id(cr, uid, ids, event_id, part)
        # this updates the dictionary
        data.update(d['value'])
        addr = res_obj.address_get(cr, uid, [part])
        if addr:
            if addr.has_key('default'):
                job_ids = job_obj.search(cr, uid, [('address_id', '=', addr['default'])])
                if job_ids:
                    data['contact_id'] = job_obj.browse(cr, uid, job_ids[0]).contact_id.id
                    d = self.onchange_contact_id(cr, uid, ids, data['contact_id'], part)
                    data.update(d['value'])
        return {'value': data}

    def onchange_partner_invoice_id(self, cr, uid, ids, event_id, partner_invoice_id):
        """This function returns value of Product unit Price based on Invoiced partner.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Registration IDs
        @param event_id: Event ID
        @param partner_invoice_id: Partner Invoice ID
        """
        data = {}
        context = {}
        event_obj = self.pool.get('event.event')
        prod_obj = self.pool.get('product.product')
        res_obj = self.pool.get('res.partner')

        data['unit_price']=False
        if not event_id:
            return {'value': data}
        data_event =  event_obj.browse(cr, uid, event_id, context=context)
        if data_event.product_id:
            data['event_product'] = data_event.product_id.name
            pricelist_id = data_event.pricelist_id and data_event.pricelist_id.id or False
            if partner_invoice_id:
                partner = res_obj.browse(cr, uid, partner_invoice_id, context=context)
                pricelist_id = pricelist_id or partner.property_product_pricelist.id
            unit_price = prod_obj._product_price(cr, uid, [data_event.product_id.id], False, False, {'pricelist': pricelist_id})[data_event.product_id.id]
            if not unit_price:
                unit_price = data_event.unit_price
            data['unit_price'] = unit_price
        return {'value': data}

event_registration()

class event_registration_badge(osv.osv):
    _name = 'event.registration.badge'
    _description = __doc__
    _columns = {
        "registration_id": fields.many2one('event.registration', 'Registration', required=True),
        "title": fields.char('Title', size=128),
        "name": fields.char('Name', size=128, required=True),
        "address_id": fields.many2one('res.partner.address', 'Address'),
    }

event_registration_badge()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
