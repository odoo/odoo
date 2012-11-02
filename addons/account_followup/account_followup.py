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
from datetime import date
import time

class followup(osv.osv):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        'followup_line': fields.one2many('account_followup.followup.line', 'followup_id', 'Follow-up'),
        'company_id': fields.many2one('res.company', 'Company', required=True),        
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account_followup.followup', context=c),
    }
    
followup()

class followup_line(osv.osv):
    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of follow-up lines."),
        'delay': fields.integer('Days of delay'),
        'start': fields.selection([('days','Net Days'),('end_of_month','End of Month')], 'Type of Term', size=64, required=True),
        'followup_id': fields.many2one('account_followup.followup', 'Follow Ups', required=True, ondelete="cascade"),
        'description': fields.text('Printed Message', translate=True),
        'send_email':fields.boolean('Send email', help="When processing, it will send an email"),
        'send_letter':fields.boolean('Send letter'),
        'phonecall':fields.boolean('Phone call'), 
        'email_template_id':fields.many2one('email.template', 'Email template', required = False, ondelete='set null'), 
        'email_body':fields.related('email_template_id', 'body_html', type='text', string="Email Message"), 
    }
    _defaults = {
        'start': 'days',
        'send_email': True,
        'send_letter': False,
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

followup_line()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _columns = {
        'followup_line_id': fields.many2one('account_followup.followup.line', 'Follow-up Level'),
        'followup_date': fields.date('Latest Follow-up', select=True),
        'payment_commitment':fields.text('Commitment'),
        'payment_date':fields.date('Date'),
        #'payment_note':fields.text('Payment note'),
        'payment_next_action':fields.text('New action'),
    }

account_move_line()

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'follow_up_msg': fields.text('Follow-up Message', translate=True),
        
    }

    _defaults = {
        'follow_up_msg': '''
Date: %(date)s

Dear %(partner_name)s,

Please find in attachment a reminder of all your unpaid invoices, for a total amount due of:

%(followup_amount).2f %(company_currency)s

Thanks,
--
%(user_signature)s
%(company_name)s
        '''
    }

res_company()



class res_partner(osv.osv):


    def _get_latest_followup_date(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids): 


            accountmovelines = partner.accountmoveline_ids
            #max(x.followup_date for x in accountmovelines)
            #latest_date = lambda a: date(2011, 1, 1)
            #for accountmoveline in accountmovelines:
            #    if (accountmoveline.followup_date != False) and (latest_date < accountmoveline.followup_date):
            #        latest_date = accountmoveline.followup_date
            #if accountmovelines:
            amls2 = filter(lambda a: (a.state != 'draft') and (a.debit > 0), accountmovelines)
            res[partner.id] = max(x.followup_date for x in amls2) if len(amls2) else False
            #else:
            #    res[partner.id] = False

            #res[partner.id] = max(x.followup_date for x in accountmovelines) if len(accountmovelines) else False
        return res

   

    
    def _get_latest_followup_level_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):
            amls = partner.accountmoveline_ids
            level_id = 0
            level_days = False  #TO BE IMPROVED with boolean checking first time or by using MAX
            latest_level = False            
            res[partner.id] = False
            for accountmoveline in amls:
                if (accountmoveline.followup_line_id != False) and (not level_days or level_days < accountmoveline.followup_line_id.delay): 
                # and (accountmoveline.debit > 0):   (accountmoveline.state != "draft") and
                #and  (accountmoveline.reconcile_id == None)
                    level_days = accountmoveline.followup_line_id.delay
                    latest_level = accountmoveline.followup_line_id.id
                    res[partner.id] = latest_level
            #res[partner.id] = max(x.followup_line_id.delay for x in amls) if len(amls) else False
        return res

    def get_latest_followup_level(self):
        amls = self.accountmoveline_ids

    def _get_next_followup_level_id_optimized(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):            
            latest_id = partner.latest_followup_level_id
            if latest_id:
                latest = latest_id
            else:
                latest = False

            delay = False
            newlevel = False
            if latest: #if latest exists                
                newlevel = latest.id
                old_delay = latest.delay
            else:
                old_delay = False
            fl_ar = self.pool.get('account_followup.followup.line').search(cr, uid, [('followup_id.company_id.id','=', partner.company_id.id)])
            
            for fl_obj in self.pool.get('account_followup.followup.line').browse(cr, uid, fl_ar):
                if not old_delay: 
                    if not delay or fl_obj.delay < delay: 
                        delay = fl_obj.delay
                        newlevel = fl_obj.id
                else:
                    if (not delay and (fl_obj.delay > old_delay)) or ((fl_obj.delay < delay) and (fl_obj.delay > old_delay)):
                        delay = fl_obj.delay
                        newlevel = fl_obj.id
            res[partner.id] = newlevel
            #Now search one level higher
        return res


    def _get_next_followup_level_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):            
            latest_id = self._get_latest_followup_level_id(cr, uid, [partner.id], name, arg, context)[partner.id]
            if latest_id:
                latest = self.pool.get('account_followup.followup.line').browse(cr, uid, [latest_id], context)[0]
            else:
                latest = False

            delay = False
            newlevel = False
            if latest: #if latest exists                
                newlevel = latest.id
                old_delay = latest.delay
            else:
                old_delay = False
            fl_ar = self.pool.get('account_followup.followup.line').search(cr, uid, [('followup_id.company_id.id','=', partner.company_id.id)])
            
            for fl_obj in self.pool.get('account_followup.followup.line').browse(cr, uid, fl_ar):
                if not old_delay: 
                    if not delay or fl_obj.delay < delay: 
                        delay = fl_obj.delay
                        newlevel = fl_obj.id
                else:
                    if (not delay and (fl_obj.delay > old_delay)) or ((fl_obj.delay < delay) and (fl_obj.delay > old_delay)):
                        delay = fl_obj.delay
                        newlevel = fl_obj.id
            res[partner.id] = newlevel
            #Now search one level higher
        return res



    def _get_amount(self, cr, uid, ids, name, arg, context=None):
        ''' 
         Get the total outstanding amount in the account move lines
        '''
        res={}
        for partner in self.browse(cr, uid, ids, context):
            res[partner.id] = 0.0
            for aml in partner.accountmoveline_ids:
                if ((not aml.date_maturity) and (aml.date > fields.date.context_today(cr, uid, context))) or (aml.date_maturity > fields.date.context_today(cr, uid, context)):
                     res[partner.id] = res[partner.id] + aml.debit
        return res


    def do_partner_phonecall(self, cr, uid, partner_ids, context=None): 
        #partners = self.browse(cr, uid, partner_ids, context)
        #print partner_ids
        #print "Testing: " ,  fields.date.context_today(cr, uid, context)
        self.write(cr, uid, partner_ids, {'payment_next_action_date': fields.date.context_today(cr, uid, context),}, context)



    def do_partner_print(self, cr, uid, partner_ids, data, context=None):        
        #data.update({'date': context['date']})
        if not partner_ids: 
            return {}
        data['partner_ids'] = partner_ids
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
        #get the mail template to use
        mail_template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_followup', 'email_template_account_followup')
        mtp = self.pool.get('email.template')
        #mtp.subject = "Invoices overdue"
        #user_obj = self.pool.get('res.users')
        #mtp.email_from = user_obj.browse(cr, uid, uid, context=context)
        for partner in self.browse(cr, uid, partner_ids, context):
            
            #Get max level of ids
            if partner.latest_followup_level_id.email_template_id != False:                
                #print "From latest followup level", partner.latest_followup_level_id.email_template_id.id
                mtp.send_mail(cr, uid, partner.latest_followup_level_id.email_template_id.id, partner.id, context=context)
            else:
                #print "From mail template", mail_template_id.id
                mtp.send_mail(cr, uid, mail_template_id.id, partner.id, context=context)

        #complete the mail body with partner information
        #(to be discussed with fp) attach the report to the mail or include the move lines in the mail body
        #send the mail (need to check the function name)

        
#        mod_obj = self.pool.get('ir.model.data')
#        move_obj = self.pool.get('account.move.line')
#        user_obj = self.pool.get('res.users')
#
#        if context is None:
#            context = {}
#        data = self.browse(cr, uid, ids, context=context)[0]
#        stat_by_partner_line_ids = [partner_id.id for partner_id in data.partner_ids]
#        partners = [stat_by_partner_line / 10000 for stat_by_partner_line in stat_by_partner_line_ids]
#        model_data_ids = mod_obj.search(cr, uid, [('model','=','ir.ui.view'),('name','=','view_account_followup_print_all_msg')], context=context)
#        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
#        if True: #should not depend on this
#            msg_sent = ''
#            msg_unsent = ''
#            data_user = user_obj.browse(cr, uid, uid, context=context)
#            for partner in self.pool.get('res.partner').browse(cr, uid, partners, context=context):
#                if partner.next_followup_level_id.send_email:
#                    ids_lines = move_obj.search(cr,uid,[('partner_id','=',partner.id),('reconcile_id','=',False),('account_id.type','in',['receivable']),('company_id','=',context.get('company_id', False))])
#                    data_lines = move_obj.browse(cr, uid, ids_lines, context=context)
#                    total_amt = 0.0
#                    for line in data_lines:
#                        total_amt += line.debit - line.credit
#                    dest = False
#                    if partner:
#                        dest = [partner.email]
#                    if not data.partner_lang:
#                        body = data.email_body 
#                    else:
#                        cxt = context.copy()
#                        cxt['lang'] = partner.lang
#                        body = user_obj.browse(cr, uid, uid, context=cxt).company_id.follow_up_msg
#                    move_line = ''
#                    subtotal_due = 0.0
#                    subtotal_paid = 0.0
#                    subtotal_maturity = 0.0
#                    balance = 0.0
#                    l = '--------------------------------------------------------------------------------------------------------------------------'
#                    head = l+ '\n' + 'Date'.rjust(10) + '\t' + 'Description'.rjust(10) + '\t' + 'Ref'.rjust(10) + '\t' + 'Due date'.rjust(10) + '\t' + 'Due'.rjust(10) + '\t' + 'Paid'.rjust(10) + '\t' + 'Maturity'.rjust(10) + '\t' + 'Litigation'.rjust(10) + '\n' + l
#                    for i in data_lines:
#                        maturity = 0.00
#                        if i.date_maturity < time.strftime('%Y-%m-%d') and (i.debit - i.credit):
#                            maturity = i.debit - i.credit
#                        subtotal_due = subtotal_due + i.debit
#                        subtotal_paid = subtotal_paid + i.credit
#                        subtotal_maturity = subtotal_maturity + int(maturity)
#                        balance = balance + (i.debit - i.credit)
#                        move_line = move_line + (i.date).rjust(10) + '\t'+ (i.name).rjust(10) + '\t'+ (i.ref or '').rjust(10) + '\t' + (i.date_maturity or '').rjust(10) + '\t' + str(i.debit).rjust(10)  + '\t' + str(i.credit).rjust(10)  + '\t' + str(maturity).rjust(10) + '\t' + str(i.blocked).rjust(10) + '\n'
#                    move_line = move_line + l + '\n'+ '\t\t\t' + 'Sub total'.rjust(35) + '\t' + (str(subtotal_due) or '').rjust(10) + '\t' + (str(subtotal_paid) or '').rjust(10) + '\t' + (str(subtotal_maturity) or '').rjust(10)+ '\n'
#                    move_line = move_line + '\t\t\t' + 'Balance'.rjust(33) + '\t' + str(balance).rjust(10) + '\n' + l
#                    val = {
#                        'partner_name':partner.name,
#                        'followup_amount':total_amt,
#                        'user_signature':data_user.name,
#                        'company_name':data_user.company_id.name,
#                        'company_currency':data_user.company_id.currency_id.name,
#                        'line':move_line,
#                        'heading': head,
#                        'date':time.strftime('%Y-%m-%d'),
#                    }
#                    body = body%val
#                    sub = tools.ustr(data.email_subject)
#                    msg = ''
#                    if dest:
#                        try:
#                            vals = {'state': 'outgoing',
#                                    'subject': sub,
#                                    'body_html': '<pre>%s</pre>' % body,
#                                    'email_to': dest,
#                                    'email_from': data_user.email or tools.config.options['email_from']}
#                            self.pool.get('mail.mail').create(cr, uid, vals, context=context)
#                            msg_sent += partner.name + '\n'
#                        except Exception, e:
#                            raise osv.except_osv('Error !', e )
#                    else:
#                        msg += partner.name + '\n'
#                        msg_unsent += msg
#            if not msg_unsent:
#                summary = _("All Emails have been successfully sent to Partners:.\n\n%s") % msg_sent
#            else:
#                msg_unsent = _("Email not sent to following Partners, Email not available !\n\n%s") % msg_unsent
#                msg_sent = msg_sent and _("\n\nEmail sent to following Partners successfully. !\n\n%s") % msg_sent
#                line = '=========================================================================='
#                summary = msg_unsent + line + msg_sent
#            context.update({'summary': summary})
#        else:
#            context.update({'summary': '\n\n\nEmail has not been sent to any partner. If you want to send it, please tick send email confirmation on wizard.'})
#
#        return {
#            'name': _('Followup Summary'),
#            'view_type': 'form',
#            'context': context,
#            'view_mode': 'tree,form',
#            'res_model': 'account.followup.print.all',
#            'views': [(resource_id,'form')],
#            'type': 'ir.actions.act_window',
#            'target': 'new',
#            'nodestroy': True
#            }


    def action_done(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids,  {'payment_next_action_date': False, 'payment_next_action':''}, context)
        
            
    

    _inherit = "res.partner"
    _columns = {
        'payment_responsible_id':fields.many2one('res.users', ondelete='set null', string='Responsible', help="Responsible"), 
        #'payment_followup_level_id':fields.many2one('account_followup.followup.line', 'Followup line'),
        'payment_note':fields.text('Payment note', help="Payment note"), 
        'payment_next_action':fields.text('Next action', help="Write here the comments of your customer"), #Just a note
        'payment_next_action_date':fields.date('Next action date', help="Next date to take action"), # next action date
        'accountmoveline_ids':fields.one2many('account.move.line', 'partner_id', domain=['&', ('debit', '>', 0.0), '&', ('reconcile_id', '=', False), '&', 
            ('account_id.active','=', True), '&', ('account_id.type', '=', 'receivable'), ('state', '!=', 'draft')]), 
        'latest_followup_date':fields.function(_get_latest_followup_date, method=True, type='date', string="latest followup date", store=True), 
        'latest_followup_level_id':fields.function(_get_latest_followup_level_id, method=True, 
            type='many2one', relation='account_followup.followup.line', string="Latest Followup Level", store=True), 
        'next_followup_level_id':fields.function(_get_next_followup_level_id_optimized, method=True, type='many2one', relation='account_followup.followup.line', string="Next Level", help="Next level that will be printed"),
        'payment_amount_outstanding':fields.function(_get_amount, method=True, type='float', string="Amount Overdue", store=True),
    }

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
