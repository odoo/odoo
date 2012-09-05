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

class account_followup_print(osv.osv_memory):
    _name = 'account.followup.print'
    _description = 'Print Follow-up & Send Mail to Customers'
    _columns = {
        'date': fields.date('Follow-up Sending Date', required=True, help="This field allow you to select a forecast date to plan your follow-ups"),
        'followup_id': fields.many2one('account_followup.followup', 'Follow-Up', required=True),
    }

    def _get_followup(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model', 'ir.ui.menu') == 'account_followup.followup':
            return context.get('active_id', False)
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        followp_id = self.pool.get('account_followup.followup').search(cr, uid, [('company_id', '=', company_id)], context=context)
        return followp_id and followp_id[0] or False

    def do_continue(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')

        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        model_data_ids = mod_obj.search(cr, uid, [('model','=','ir.ui.view'),('name','=','view_account_followup_print_all')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context.update({'followup_id': data.followup_id.id, 'date': data.date, 'company_id': data.followup_id.company_id.id})
        return {
            'name': _('Select Partners'),
            'view_type': 'form',
            'context': context,
            'view_mode': 'tree,form',
            'res_model': 'account.followup.print.all',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
    }

    _defaults = {
         'date': lambda *a: time.strftime('%Y-%m-%d'),
         'followup_id': _get_followup,
    }
account_followup_print()

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
                    l.partner_id IS NOT NULL
                    GROUP BY
                    l.partner_id, l.company_id
            )""")
account_followup_stat_by_partner()

class account_followup_print_all(osv.osv_memory):
    _name = 'account.followup.print.all'
    _description = 'Print Follow-up & Send Mail to Customers'
    _columns = {
        'partner_ids': fields.many2many('account_followup.stat.by.partner', 'partner_stat_rel', 'osv_memory_id', 'partner_id', 'Partners', required=True),
        'email_conf': fields.boolean('Send Email Confirmation'),
        'email_subject': fields.char('Email Subject', size=64),
        'partner_lang': fields.boolean('Send Email in Partner Language', help='Do not change message text, if you want to send email in partner language, or configure from company'),
        'email_body': fields.text('Email Body'),
        'summary': fields.text('Summary', required=True, readonly=True),
        'test_print': fields.boolean('Test Print', help='Check if you want to print follow-ups without changing follow-ups level.')
    }
    def _get_summary(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('summary', '')

    def _get_partners(self, cr, uid, context=None):
        return self._get_partners_followp(cr, uid, [], context=context)['partner_ids']

    def _get_msg(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.follow_up_msg

    _defaults = {
         'email_body': _get_msg,
         'email_subject': _('Invoices Reminder'),
         'partner_lang': True,
         'partner_ids': _get_partners,
         'summary': _get_summary,
    }

    def _get_partners_followp(self, cr, uid, ids, context=None):
        data = {}
        if context is None:
            context = {}
        if ids:
            data = self.browse(cr, uid, ids, context=context)[0]
        company_id = 'company_id' in context and context['company_id'] or data.company_id.id

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
                "AND (l.company_id = %s) "\
            "ORDER BY l.date", (company_id,))
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
        for result in cr.dictfetchall():
            delay = datetime.timedelta(days=result['delay'])
            fups[old] = (current_date - delay, result['id'])
            if result['start'] == 'end_of_month':
                fups[old][0].replace(day=1)
            old = result['id']

        fups[old] = (datetime.date(datetime.MAXYEAR, 12, 31), old)

        partner_list = []
        to_update = {}
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

    def do_mail(self ,cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        move_obj = self.pool.get('account.move.line')
        user_obj = self.pool.get('res.users')

        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        stat_by_partner_line_ids = [partner_id.id for partner_id in data.partner_ids]
        partners = [stat_by_partner_line / 10000 for stat_by_partner_line in stat_by_partner_line_ids]
        model_data_ids = mod_obj.search(cr, uid, [('model','=','ir.ui.view'),('name','=','view_account_followup_print_all_msg')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        if data.email_conf:
            msg_sent = ''
            msg_unsent = ''
            data_user = user_obj.browse(cr, uid, uid, context=context)
            for partner in self.pool.get('res.partner').browse(cr, uid, partners, context=context):
                ids_lines = move_obj.search(cr,uid,[('partner_id','=',partner.id),('reconcile_id','=',False),('account_id.type','in',['receivable']),('company_id','=',context.get('company_id', False))])
                data_lines = move_obj.browse(cr, uid, ids_lines, context=context)
                total_amt = 0.0
                for line in data_lines:
                    total_amt += line.debit - line.credit
                dest = False
                if partner:
                    if partner.type=='contact':
                        if adr.email:
                            dest = [partner.email]
                    if (not dest) and partner.type=='default':
                        if partner.email:
                            dest = [partner.email]
                if not data.partner_lang:
                    body = data.email_body
                else:
                    cxt = context.copy()
                    cxt['lang'] = partner.lang
                    body = user_obj.browse(cr, uid, uid, context=cxt).company_id.follow_up_msg
                move_line = ''
                subtotal_due = 0.0
                subtotal_paid = 0.0
                subtotal_maturity = 0.0
                balance = 0.0
                l = '--------------------------------------------------------------------------------------------------------------------------'
                head = l+ '\n' + 'Date'.rjust(10) + '\t' + 'Description'.rjust(10) + '\t' + 'Ref'.rjust(10) + '\t' + 'Due date'.rjust(10) + '\t' + 'Due'.rjust(10) + '\t' + 'Paid'.rjust(10) + '\t' + 'Maturity'.rjust(10) + '\t' + 'Litigation'.rjust(10) + '\n' + l
                for i in data_lines:
                    maturity = 0.00
                    if i.date_maturity < time.strftime('%Y-%m-%d') and (i.debit - i.credit):
                        maturity = i.debit - i.credit
                    subtotal_due = subtotal_due + i.debit
                    subtotal_paid = subtotal_paid + i.credit
                    subtotal_maturity = subtotal_maturity + int(maturity)
                    balance = balance + (i.debit - i.credit)
                    move_line = move_line + (i.date).rjust(10) + '\t'+ (i.name).rjust(10) + '\t'+ (i.ref or '').rjust(10) + '\t' + (i.date_maturity or '').rjust(10) + '\t' + str(i.debit).rjust(10)  + '\t' + str(i.credit).rjust(10)  + '\t' + str(maturity).rjust(10) + '\t' + str(i.blocked).rjust(10) + '\n'
                move_line = move_line + l + '\n'+ '\t\t\t' + 'Sub total'.rjust(35) + '\t' + (str(subtotal_due) or '').rjust(10) + '\t' + (str(subtotal_paid) or '').rjust(10) + '\t' + (str(subtotal_maturity) or '').rjust(10)+ '\n'
                move_line = move_line + '\t\t\t' + 'Balance'.rjust(33) + '\t' + str(balance).rjust(10) + '\n' + l
                val = {
                    'partner_name':partner.name,
                    'followup_amount':total_amt,
                    'user_signature':data_user.name,
                    'company_name':data_user.company_id.name,
                    'company_currency':data_user.company_id.currency_id.name,
                    'line':move_line,
                    'heading': head,
                    'date':time.strftime('%Y-%m-%d'),
                }
                body = body%val
                sub = tools.ustr(data.email_subject)
                msg = ''
                if dest:
                    try:
                        vals = {'state': 'outgoing',
                                'subject': sub,
                                'body_html': '<pre>%s</pre>' % body,
                                'email_to': dest,
                                'email_from': data_user.email or tools.config.options['email_from']}
                        self.pool.get('mail.mail').create(cr, uid, vals, context=context)
                        msg_sent += partner.name + '\n'
                    except Exception, e:
                        raise osv.except_osv('Error !', e )
                else:
                    msg += partner.name + '\n'
                    msg_unsent += msg
            if not msg_unsent:
                summary = _("All Emails have been successfully sent to Partners:.\n\n%s") % msg_sent
            else:
                msg_unsent = _("Email not sent to following Partners, Email not available !\n\n%s") % msg_unsent
                msg_sent = msg_sent and _("\n\nEmail sent to following Partners successfully. !\n\n%s") % msg_sent
                line = '=========================================================================='
                summary = msg_unsent + line + msg_sent
            context.update({'summary': summary})
        else:
            context.update({'summary': '\n\n\nEmail has not been sent to any partner. If you want to send it, please tick send email confirmation on wizard.'})

        return {
            'name': _('Followup Summary'),
            'view_type': 'form',
            'context': context,
            'view_mode': 'tree,form',
            'res_model': 'account.followup.print.all',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True
            }

    def do_print(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context=context)[0]
        res = self._get_partners_followp(cr, uid, ids, context)['to_update']
        to_update = res
        data['followup_id'] = 'followup_id' in context and context['followup_id'] or False
        date = 'date' in context and context['date'] or data['date']
        if not data['test_print']:
            for id in to_update.keys():
                if to_update[id]['partner_id'] in data['partner_ids']:
                    cr.execute(
                        "UPDATE account_move_line "\
                        "SET followup_line_id=%s, followup_date=%s "\
                        "WHERE id=%s",
                        (to_update[id]['level'],
                        date, int(id),))
        data.update({'date': context['date']})
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

account_followup_print_all()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
