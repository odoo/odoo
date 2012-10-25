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
        'send_letter':fields.boolean('Print email'),
        'phonecall':fields.boolean('Phone call'), 
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
            level_days = -1000  #TO BE IMPROVED with boolean checking first time or by using MAX
            latest_level = False            
            res[partner.id] = False

            for accountmoveline in amls:
                if (accountmoveline.followup_line_id != False) and (level_days < accountmoveline.followup_line_id.delay): 
                # and (accountmoveline.debit > 0):   (accountmoveline.state != "draft") and
                #and  (accountmoveline.reconcile_id == None)
                    level_days = accountmoveline.followup_line_id.delay
                    latest_level = accountmoveline.followup_line_id.id
                    res[partner.id] = latest_level
            #res[partner.id] = max(x.followup_line_id.delay for x in amls) if len(amls) else False
        return res

    def get_latest_followup_level(self):
        amls = self.accountmoveline_ids


    def _get_next_followup_level_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):            
            latest_id = self._get_latest_followup_level_id(cr, uid, [partner.id], name, arg, context)[partner.id]
            latest = self.pool.get('account_followup.followup.line').browse(cr, uid, [latest_id], context)[0]
            delay = False
            newlevel = False
            if latest: #if latest exists
                newlevel = latest.id
                old_delay = latest.delay
            else:
                old_delay = False

            for fl in self.pool.get('account_followup.followup.line').search(cr, uid, []):  #('followup_id.company_id','=',latest.followup_id.company_id)
                fl_obj = self.pool.get('account_followup.followup.line').browse(cr, uid, [fl])[0]
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
            type='many2one', relation='account_followup.followup.line', string="latest followup level", store=True), 
        'next_followup_level_id':fields.function(_get_next_followup_level_id, method=True, type='many2one', relation='account_followup.followup.line', string="next level"),
    }


res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
