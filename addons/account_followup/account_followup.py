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
from lxml import etree

from tools.translate import _


class followup(osv.osv):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'
    _columns = {
        'followup_line': fields.one2many('account_followup.followup.line', 'followup_id', 'Follow-up'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'name': fields.related('company_id', 'name', string = "Name"),
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account_followup.followup', context=c),
    }
    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Only one follow-up per company is allowed')] 



class followup_line(osv.osv):

    def _get_default_template(self, cr, uid, ids, context=None):
        dummy, templ = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_followup', 'email_template_account_followup_default')
        return templ
    
    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    _columns = {
        'name': fields.char('Follow-Up Action', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of follow-up lines."),
        'delay': fields.integer('Due Days', help="The number of days after the due date of the invoice to wait before sending the reminder.  Could be negative if you want to send a polite alert beforehand.", required=True),
        'followup_id': fields.many2one('account_followup.followup', 'Follow Ups', required=True, ondelete="cascade"),
        'description': fields.text('Printed Message', translate=True),
        'send_email':fields.boolean('Send an Email', help="When processing, it will send an email"),
        'send_letter':fields.boolean('Send a Letter', help="When processing, it will print a letter"),
        'manual_action':fields.boolean('Manual Action', help="When processing, it will set the manual action to be taken for that customer. "),
        'manual_action_note':fields.text('Action To Do', placeholder="e.g. Give a phone call, check with others , ..."),
        'manual_action_responsible_id':fields.many2one('res.users', 'Assign a Responsible', ondelete='set null'),
        'email_template_id':fields.many2one('email.template', 'Email Template', ondelete='set null'),
    }
    _order = 'delay'
    _sql_constraints = [('days_uniq', 'unique(followup_id, delay)', 'Days of the follow-up levels must be different')]
    _defaults = {
        'send_email': True,
        'send_letter': False,
        'manual_action':False,
        'description': """
        Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. Do not hesitate to contact our accounting department at (+32).10.68.94.39.

Best Regards,
""",
    'email_template_id': _get_default_template,
    }


    def _check_description(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.description:
                try:
                    line.description % {'partner_name': '', 'date':'', 'user_signature': '', 'company_name': ''}
                except:
                    return False
        return True

    _constraints = [
        (_check_description, 'Your description is invalid, use the right legend or %% if you want to use the percent character.', ['description']),
    ]


class account_move_line(osv.osv):

    def _get_result(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for aml in self.browse(cr, uid, ids, context=context):
            res[aml.id] = aml.debit - aml.credit
        return res

    _inherit = 'account.move.line'
    _columns = {
        'followup_line_id': fields.many2one('account_followup.followup.line', 'Follow-up Level', 
                                        ondelete='restrict'), #restrict deletion of the followup line
        'followup_date': fields.date('Latest Follow-up', select=True),
        'result':fields.function(_get_result, type='float', method=True, 
                                string="Balance") #'balance' field is not the same
    }



class email_template(osv.osv):
    _inherit = 'email.template'

    # Adds current_date to the context.  That way it can be used to put
    # the account move lines in bold that are overdue in the email
    def render_template(self, cr, uid, template, model, res_id, context=None):
        context['current_date'] = fields.date.context_today(cr, uid, context)
        return super(email_template, self).render_template(cr, uid, template, model, res_id, context=context)



class res_partner(osv.osv):

    def fields_view_get(self, cr, uid, view_id=None, view_type=None, context=None, toolbar=False, submenu=False):
        res = super(res_partner, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context,
                                                       toolbar=toolbar, submenu=submenu)
        if view_type == 'form' and context and 'Followupfirst' in context.keys() and context['Followupfirst'] == True:
            doc = etree.XML(res['arch'], parser=None, base_url=None)
            first_node = doc.xpath("//page[@string='Payment Follow-up']")
            root = first_node[0].getparent()
            root.insert(0, first_node[0])
            res['arch'] = etree.tostring(doc)
        return res




    def _get_latest(self, cr, uid, ids, names, arg, context=None, company_id=None):
        res={}
        if company_id == None:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        else:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            amls = partner.unreconciled_aml_ids
            latest_date = False
            latest_level = False
            latest_days = False
            latest_level_without_lit = False
            latest_days_without_lit = False
            for aml in amls:
                if (aml.company_id == company) and (aml.followup_line_id != False) and (not latest_days or latest_days < aml.followup_line_id.delay):
                    latest_days = aml.followup_line_id.delay
                    latest_level = aml.followup_line_id.id
                if (aml.company_id == company) and (not latest_date or latest_date < aml.followup_date):
                    latest_date = aml.followup_date
                if (aml.company_id == company) and (aml.blocked == False) and (aml.followup_line_id != False and 
                            (not latest_days_without_lit or latest_days_without_lit < aml.followup_line_id.delay)):
                    latest_days_without_lit =  aml.followup_line_id.delay
                    latest_level_without_lit = aml.followup_line_id.id
            res[partner.id] = {'latest_followup_date': latest_date,
                               'latest_followup_level_id': latest_level,
                               'latest_followup_level_id_without_lit': latest_level_without_lit}
        return res


    def do_partner_manual_action(self, cr, uid, partner_ids, context=None): 
        #partner_ids -> res.partner
        for partner in self.browse(cr, uid, partner_ids, context=context):
            #Check action: check if the action was not empty, if not add
            action_text= ""
            if partner.payment_next_action:
                action_text = (partner.payment_next_action or '') + "\n" + (partner.latest_followup_level_id_without_lit.manual_action_note or '')
            else:
                action_text = partner.latest_followup_level_id_without_lit.manual_action_note or ''
            
            #Check date: put the minimum date if it existed already
            action_date = (partner.payment_next_action_date and min(partner.payment_next_action_date, fields.date.context_today(cr, uid, context))
                           ) or fields.date.context_today(cr, uid, context)
            
            # Check responsible: if partner has not got a responsible already, take from follow-up
            responsible_id = False
            if partner.payment_responsible_id:
                responsible_id = partner.payment_responsible_id.id
            else:
                p = partner.latest_followup_level_id_without_lit.manual_action_responsible_id
                responsible_id = p and p.id or False
            self.write(cr, uid, [partner.id], {'payment_next_action_date': action_date,
                                        'payment_next_action': action_text,
                                        'payment_responsible_id': responsible_id})


    def do_partner_print(self, cr, uid, wizard_partner_ids, data, context=None):
        #wizard_partner_ids are ids from special view, not from res.partner
        if not wizard_partner_ids:
            return {}
        data['partner_ids'] = wizard_partner_ids
        datas = {
             'ids': [],
             'model': 'account_followup.followup',
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account_followup.followup.print',
            'datas': datas,
            }

    def do_partner_mail(self, cr, uid, partner_ids, context=None):
        #partner_ids are res.partner ids
        # If not defined by latest follow-up level, it will be the default template if it can find it
        mtp = self.pool.get('email.template')
        unknown_mails = 0
        for partner in self.browse(cr, uid, partner_ids, context=context):
            if partner.email != False and partner.email != '' and partner.email != ' ':
                p = partner.latest_followup_level_id_without_lit
                if p and p.send_email and p.email_template_id.id != False:
                    mtp.send_mail(cr, uid, p.email_template_id.id, partner.id, context=context)
                else:
                    mail_template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 
                                                    'account_followup', 'email_template_account_followup_default')
                    mtp.send_mail(cr, uid, mail_template_id[1], partner.id, context=context)
            else:
                unknown_mails = unknown_mails + 1
                action_text = _("Email not sent because of email address of partner not filled in")
                if partner.payment_next_action_date:
                    payment_action_date = min(fields.date.context_today(cr, uid, context), partner.payment_next_action_date)
                else:
                    payment_action_date = fields.date.context_today(cr, uid, context)
                if partner.payment_next_action:
                    payment_next_action = partner.payment_next_action + " + " + action_text
                else:
                    payment_next_action = action_text
                self.write(cr, uid, [partner.id], {'payment_next_action_date': payment_action_date,
                                                   'payment_next_action': payment_next_action}, context=context)
        return unknown_mails

    def action_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'payment_next_action_date': False, 'payment_next_action':'', 'payment_responsible_id': False}, context=context)

    def do_button_print(self, cr, uid, ids, context=None):
        assert(len(ids) == 1)
        self.message_post(cr, uid, [ids[0]], body=_('Printed overdue payments report'), context=context)
        datas = {
             'ids': ids,
             'model': 'res.partner',
             'form': self.read(cr, uid, ids[0], context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.overdue',
            'datas': datas,
            'nodestroy' : True
        }




    _inherit = "res.partner"
    _columns = {
        'payment_responsible_id':fields.many2one('res.users', ondelete='set null', string='Follow-up Responsible', 
                                                 help="Responsible for making sure the action happens."), 
        'payment_note':fields.text('Customer Payment Promise', help="Payment Note"),
        'payment_next_action':fields.text('Next Action',
                                    help="This is the next action to be taken by the user.  It will automatically be set when the action fields are empty and the partner gets a follow-up level that requires a manual action. "), 
        'payment_next_action_date':fields.date('Next Action Date',
                                    help="This is when further follow-up is needed.  The date will have been set to the current date if the action fields are empty and the partner gets a follow-up level that requires a manual action. "), 
        'unreconciled_aml_ids':fields.one2many('account.move.line', 'partner_id', domain=['&', ('reconcile_id', '=', False), '&', 
                            ('account_id.active','=', True), '&', ('account_id.type', '=', 'receivable'), ('state', '!=', 'draft')]), 
        'latest_followup_date':fields.function(_get_latest, method=True, type='date', string="Latest Follow-up Date", 
                            help="Latest date that the follow-up level of the partner was changed", 
                            store=False, 
                            multi="latest"), 
        'latest_followup_level_id':fields.function(_get_latest, method=True, 
            type='many2one', relation='account_followup.followup.line', string="Latest Follow-up Level", 
            help="The maximum follow-up level", 
            store=False, 
            multi="latest"), 
        'latest_followup_level_id_without_lit':fields.function(_get_latest, method=True, 
            type='many2one', relation='account_followup.followup.line', string="Latest Follow-up Level without litigation", 
            help="The maximum follow-up level without taking into account the account move lines with litigation", 
            store=False, 
            multi="latest"),
        
        'payment_amount_due':fields.related('credit', type='float', string="Total amount due", readonly=True),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
