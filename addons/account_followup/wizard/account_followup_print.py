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

import datetime
import time

import tools
from osv import fields, osv
from tools.translate import _

class account_followup_stat_by_partner(osv.osv):
    _name = "account_followup.stat.by.partner"
    _description = "Follow-up Statistics by Partner"
    _rec_name = 'partner_id'
    _auto = False
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'date_move':fields.date('First move', readonly=True),
        'date_move_last':fields.date('Last move', readonly=True),
        'date_followup':fields.date('Latest follow-up', readonly=True),
        'max_followup_id': fields.many2one('account_followup.followup.line',
                                    'Max Follow Up Level', readonly=True, ondelete="cascade"),
        'balance':fields.float('Balance', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_followup_stat_by_partner')
        # Here we don't have other choice but to create a virtual ID based on the concatenation
        # of the partner_id and the company_id, because if a partner is shared between 2 companies,
        # we want to see 2 lines for him in this table. It means that both company should be able
        # to send him follow-ups separately . An assumption that the number of companies will not
        # reach 10 000 records is made, what should be enough for a time.
        cr.execute("""
            create or replace view account_followup_stat_by_partner as (
                SELECT
                    l.partner_id * 10000 + l.company_id as id,
                    l.partner_id AS partner_id,
                    min(l.date) AS date_move,
                    max(l.date) AS date_move_last,
                    max(l.followup_date) AS date_followup,
                    max(l.followup_line_id) AS max_followup_id,
                    sum(l.debit - l.credit) AS balance,
                    l.company_id as company_id
                FROM
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id = a.id)
                WHERE
                    a.active AND
                    a.type = 'receivable' AND
                    l.reconcile_id is NULL AND
                    l.partner_id IS NOT NULL AND
                    (l.blocked = False)
                    GROUP BY
                    l.partner_id, l.company_id
            )""") #Blocked is to take into account litigation
account_followup_stat_by_partner()


class account_followup_sending_results(osv.osv_memory):
    
   
    def do_report(self, cr, uid, ids, context=None):
        return context['report_data']
    
    def do_done(self, cr, uid, ids, context=None):
        return {}
    
    def _get_description(self, cr, uid, context=None):
        res = ""
        if context!=None:
            res = context['description']
        return res
    
    def _get_need_printing(self, cr, uid, context=None):
        res = False
        if context!=None:
            if context['needprinting']:
                res = context['needprinting']
        return res
    
    _name = 'account.followup.sending.results'
    _description = 'Results from the sending of the different letters and emails'
    _columns  = {
            'description':fields.text("Description", required=False, readonly=True), 
            'needprinting':fields.boolean("Needs printing")
                 }
    _defaults = {
                'needprinting':_get_need_printing, 
                'description':_get_description,
            
                 }
    
account_followup_sending_results()   


class account_followup_print(osv.osv_memory):
    _name = 'account.followup.print'
    _description = 'Print Follow-up & Send Mail to Customers'
    _columns = {
        'date': fields.date('Follow-up Sending Date', required=True, help="This field allow you to select a forecast date to plan your follow-ups"),
        'followup_id': fields.many2one('account_followup.followup', 'Follow-Up', required=True, readonly = True),
        'partner_ids': fields.many2many('account_followup.stat.by.partner', 'partner_stat_rel', 'osv_memory_id', 'partner_id', 'Partners', required=True),
        'company_id':fields.related('followup_id', 'company_id', type='many2one', relation='res.company', store=True, readonly=True), 
        'email_conf': fields.boolean('Send Email Confirmation'),
        'email_subject': fields.char('Email Subject', size=64),
        'partner_lang': fields.boolean('Send Email in Partner Language', help='Do not change message text, if you want to send email in partner language, or configure from company'),
        'email_body': fields.text('Email Body'),
        'summary': fields.text('Summary', readonly=True),
        'test_print': fields.boolean('Test Print', help='Check if you want to print follow-ups without changing follow-ups level.'),       
    }

    def _get_followup(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model', 'ir.ui.menu') == 'account_followup.followup':
            return context.get('active_id', False)
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        followp_id = self.pool.get('account_followup.followup').search(cr, uid, [('company_id', '=', company_id)], context=context)
        return followp_id and followp_id[0] or False




    def process_partners(self, cr, uid, partner_ids, data, context=None):
        partner_obj = self.pool.get('res.partner')
        partner_ids_to_print = []
        nbmanuals = 0
        manuals = {}
        nbmails = 0
        nbunknownmails = 0
        nbprints = 0
        resulttext = " "
        for partner in self.pool.get('account_followup.stat.by.partner').browse(cr, uid, partner_ids, context=context):
            if partner.max_followup_id.manual_action:
                partner_obj.do_partner_manual_action(cr, uid, [partner.partner_id.id], context)
                nbmanuals = nbmanuals + 1
                key = partner.partner_id.payment_responsible_id.name or _("Nobody")
                if not key in manuals.keys():
                    manuals[key]= 1
                else:
                    manuals[key] = manuals[key] + 1
            if partner.max_followup_id.send_email:
                nbunknownmails += partner_obj.do_partner_mail(cr, uid, [partner.partner_id.id], context)
                nbmails += 1
            if partner.max_followup_id.send_letter:
                partner_ids_to_print.append(partner.id)
                nbprints += 1
                message = _("Follow-up letter of ") + "<I> " + partner.partner_id.latest_followup_level_id_without_lit.name + "</I>" + _(" will be sent")
                partner_obj.message_post(cr, uid, [partner.partner_id.id], body=message, context=context)
        if nbunknownmails == 0:
            resulttext += str(nbmails) + _(" emails sent")
        else:
            resulttext += str(nbmails) + _(" emails should have been sent, but ") + str(nbunknownmails) + _(" had unknown email addresses") + "\n <BR/> "
        resulttext += "<BR/>" + str(nbprints) + _(" letters in report") + " \n <BR/>" + str(nbmanuals) + _(" total manual action(s) assigned:")
        needprinting = False
        if nbprints > 0:
            needprinting = True
        resulttext += "<p align=\"center\">"
        for item in manuals:
            resulttext = resulttext + "<li>" + item + ":" + str(manuals[item]) +  "\n </li>"
        resulttext += "</p>"
        result = {}
        action = partner_obj.do_partner_print(cr, uid, partner_ids_to_print, data, context)
        result['needprinting'] = needprinting
        result['resulttext'] = resulttext
        result['action'] = action or {}
        return result

    def do_update_followup_level(self, cr, uid, to_update, partner_list, date, context=None):
        #update the follow-up level on account.move.line
        for id in to_update.keys():
            if to_update[id]['partner_id'] in partner_list:
                self.pool.get('account.move.line').write(cr, uid, [int(id)], {'followup_line_id': to_update[id]['level'], 'followup_date': date})

    def do_process(self, cr, uid, ids, context=None):
        tmp = self._get_partners_followp(cr, uid, ids, context=context)
        partner_list = tmp['partner_ids']
        to_update = tmp['to_update']
        date = self.browse(cr, uid, ids, context)[0].date
        data = self.read(cr, uid, ids, [], context)[0]
        data['followup_id'] = data['followup_id'][0]
        self.do_update_followup_level(cr, uid, to_update, partner_list, date, context=context)
        restot = self.process_partners(cr, uid, partner_list, data, context=context)
        res = restot['action']        
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        model_data_ids = mod_obj.search(cr, uid, [('model','=','ir.ui.view'),('name','=','view_account_followup_sending_results')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context.update({'description': restot['resulttext'], 'needprinting': restot['needprinting'], 'report_data': res})
        return {
            'name': _('Send Letters and Emails: Actions Summary'),
            'view_type': 'form',
            'context': context,
            'view_mode': 'tree,form',
            'res_model': 'account.followup.sending.results',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            }

    def _get_msg(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.follow_up_msg

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'followup_id': _get_followup,
        'email_body': "",
        'email_subject': _('Invoices Reminder'),
        'partner_lang': True,
        #'partner_ids': _get_partners,
    }

    def _get_partners_followp(self, cr, uid, ids, context=None):
        data = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        company_id = data.company_id.id

        cr.execute(
            "SELECT l.partner_id, l.followup_line_id,l.date_maturity, l.date, l.id "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
            "WHERE (l.reconcile_id IS NULL) "\
                "AND (a.type='receivable') "\
                "AND (l.state<>'draft') "\
                "AND (l.partner_id is NOT NULL) "\
                "AND (a.active) "\
                "AND (l.debit > 0) "\
                "AND (l.company_id = %s) " \
                "AND (l.blocked = False)" \
            "ORDER BY l.date", (company_id,))  #l.blocked added to take litigation into account and it is not necessary to change follow-up level of account move lines without debit
        move_lines = cr.fetchall()
        old = None
        fups = {}
        fup_id = 'followup_id' in context and context['followup_id'] or data.followup_id.id
        date = 'date' in context and context['date'] or data.date

        current_date = datetime.date(*time.strptime(date,
            '%Y-%m-%d')[:3])
        cr.execute(
            "SELECT * "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY delay", (fup_id,))
        
        #Create dictionary of tuples where first element is the date to compare with the due date and second element is the id of the next level
        for result in cr.dictfetchall():
            delay = datetime.timedelta(days=result['delay'])
            fups[old] = (current_date - delay, result['id'])
            #if result['start'] == 'end_of_month': -> did not do anything
            #    print "Important date change start:", fups[old][0]#.strftime("%Y-%m%-%d")
            #   fups[old][0].replace(day=1)
            #    print "Important date change end:", fups[old][0]#.strftime("%Y-%m%-%d")
                #fups[old][0] = fups[old][0] + datetime.timedelta(months=1)
            old = result['id']
        #fups[old] = (datetime.date(datetime.MAXYEAR, 12, 31), old) --> By commenting this, last level won't be printed again and again
        fups 
        partner_list = []
        to_update = {}
        
        #Fill dictionary of accountmovelines to_update with the partners that need to be updated
        for partner_id, followup_line_id, date_maturity,date, id in move_lines:
            if not partner_id:
                continue
            if followup_line_id not in fups:
                continue
            stat_line_id = partner_id * 10000 + company_id
            if date_maturity:
                if date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                    if stat_line_id not in partner_list:
                        partner_list.append(stat_line_id)
                    to_update[str(id)]= {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                if stat_line_id not in partner_list:
                    partner_list.append(stat_line_id)
                to_update[str(id)]= {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
        return {'partner_ids': partner_list, 'to_update': to_update}

account_followup_print()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
