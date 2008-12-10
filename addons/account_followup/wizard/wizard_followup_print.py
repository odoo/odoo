# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import datetime
import pooler
import time

import tools
from osv import fields, osv
from tools.translate import _

_followup_wizard_date_form = """<?xml version="1.0"?>
<form string="Select a date">
    <field name="date"/>
</form>"""

_followup_wizard_date_fields = {
        'date': {'string': 'Date', 'type': 'date', 'required': True},
}

form = """<?xml version="1.0"?>
<form string="Mail">
    <field name="mail_sent" colspan="4"/>
    <newline/>
    <newline/>
    <separator string="Mail not sent to following Partners , Email not available !" colspan="4"/>
    <field name="mail_notsent" colspan="4" nolabel="1"/>
</form>"""

fields = {
    'mail_sent': {'string':'Number of Mail sent', 'type':'char', 'readonly':True },
    'mail_notsent': {'string':'Error Messages', 'type':'text', 'readonly':True , 'nolabel':'1'},
        }

_followup_wizard_all_form = """<?xml version="1.0"?>
<form string="Select partners" colspan="4">
    <notebook>
        <page string="FollowUp selection">
            <separator string="Select partners to remind" colspan="4"/>
            <field name="partner_ids" colspan="4" nolabel="1"/>
        </page>
        <page string="Email confirmation">
            <field name="email_conf" colspan="4"/>
            <field name="email_subject" colspan="4"/>
            <separator string="Email body" colspan="4"/>
            <field name="email_body" colspan="4" nolabel="1"/>
            <separator string="Legend" colspan="4"/>

            <label string="%(partner_name)s: Partner name" colspan="2"/>
            <label string="%(followup_amount)s: Total Amount Due" colspan="2"/>
            <label string="%(user_signature)s: User name" colspan="2"/>
            <label string="%(company_name)s: User's Company name" colspan="2"/>
            <label string="%(line)s: Account Move lines" colspan="2"/>
            <label string="%(heading)s: Move line header" colspan="2"/>
            <label string="%(date)s: Current Date" colspan="2"/>
        </page>
    </notebook>
</form>"""

_followup_wizard_all_fields = {
    'partner_ids': {
        'string': "Partners",
        'type': 'many2many',
        'relation': 'account_followup.stat',
        'domain':"[('account_type','=','receivable')]"
    },
    'email_conf': {
        'string': "Send email confirmation",
        'type': 'boolean',
    },
    'email_subject' : {
        'string' : "Email Subject",
        'type' : "char",
        'size': 64,
        'default': 'Account Follow-up'
        },
    'email_body': {
        'string': "Email body",
        'type': 'text',
        'default': '''
Date : %(date)s

Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount staid unpaid. Please, take appropriate
measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please consider the present one as void. Do not
hesitate to contact our accounting departement at (+32).10.68.94.39.

Best regards,

%(heading)s
%(line)s

Total Amount due: %(followup_amount).2f EUR

Thanks,
--
%(user_signature)s
%(company_name)s
        '''
    }
}

class followup_all_print(wizard.interface):
    def _update_partners(self, cr, uid, data, context):
        to_update = data['form']['to_update']
        for id in to_update.keys():
            cr.execute(
                "UPDATE account_move_line "\
                "SET followup_line_id=%s, followup_date=%s "\
                "WHERE id=%s",
                (to_update[id],
                data['form']['date'], int(id),))
        return {}

    def _sendmail(self ,cr, uid, data, context):
        self._update_partners(cr, uid, data, context)
        mail_notsent = ''
        count = 0
        if data['form']['email_conf']:
            pool = pooler.get_pool(cr.dbname)
            data_user = pool.get('res.users').browse(cr,uid,uid)
            line_obj = pool.get('account_followup.stat')
            move_lines = line_obj.browse(cr,uid,data['form']['partner_ids'][0][2])
            partners = []
            dict_lines = {}
            for line in move_lines:
                partners.append(line.name)
                dict_lines[line.name.id] =line
            for partner in partners:
                ids_lines = pool.get('account.move.line').search(cr,uid,[('partner_id','=',partner.id),('reconcile_id','=',False),('account_id.type','in',['receivable','payable'])])
                data_lines = pool.get('account.move.line').browse(cr,uid,ids_lines)
                followup_data = dict_lines[partner.id]
                dest = False
                if partner.address:
                    for adr in partner.address:
                        if adr.type=='contact':
                            if adr.email:
                                dest = [adr.email]
                        if (not dest) and adr.type=='default':
                            if adr.email:
                                dest = [adr.email]
                src = tools.config.options['smtp_user']
                body=data['form']['email_body']
                total_amt = followup_data.debit - followup_data.credit
                move_line = ''
                subtotal_due = 0.0
                subtotal_paid = 0.0
                subtotal_maturity = 0.0
                balance = 0.0
                l = '--------------------------------------------------------------------------------------------------------------------------'
                head = l+ '\n' + 'Date'.rjust(10) + '\t' + 'Description'.rjust(10) + '\t' + 'Ref'.rjust(10) + '\t' + 'Maturity date'.rjust(10) + '\t' + 'Due'.rjust(10) + '\t' + 'Paid'.rjust(10) + '\t' + 'Maturity'.rjust(10) + '\t' + 'Litigation'.rjust(10) + '\n' + l
                for i in data_lines:
                    maturity = ''
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
                    'line':move_line,
                    'heading': head,
                    'date':time.strftime('%Y-%m-%d')
                }
                body = body%val
                sub = str(data['form']['email_subject'])
                if dest:
                    tools.email_send(src,dest,sub,body)
                    count = count + 1
                else:
                    mail_notsent = mail_notsent + partner.name + ','
        return {'mail_notsent' : str(mail_notsent) , 'mail_sent' : str(count)}

    def _get_partners(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        cr.execute(
            "SELECT l.partner_id, l.followup_line_id,l.date_maturity, l.date, l.id "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
            "WHERE (l.reconcile_id IS NULL) "\
                "AND (a.type='receivable') "\
                "AND (l.state<>'draft') "\
                "AND (l.reconcile_id is NULL) "\
                "AND partner_id is NOT NULL "\
                "AND a.active "\
            "ORDER BY l.date")
        move_lines = cr.fetchall()

        old = None
        fups = {}
        fup_ids = pool.get('account_followup.followup').search(cr, uid, [])
        if not fup_ids:
            raise wizard.except_wizard(_('No Follow up Defined'),
                _('You must define at least one follow up for your company !'))
        fup_id = fup_ids[0]

        current_date = datetime.date(*time.strptime(data['form']['date'],
            '%Y-%m-%d')[:3])
        cr.execute(
            "SELECT * "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY sequence", (fup_id,))
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
            if partner_id in partner_list:
                to_update[str(id)] = fups[followup_line_id][1]
            if followup_line_id not in fups:
                continue
            if date_maturity and date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                partner_list.append(partner_id)
                to_update[str(id)] = fups[followup_line_id][1]
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                partner_list.append(partner_id)
                to_update[str(id)] = fups[followup_line_id][1]
        return {'partner_ids': partner_list, 'to_update': to_update}

    def _get_date(self, cursor, user, data, context):
        return {'date': time.strftime('%Y-%m-%d')}

    states = {
        'init': {
            'actions': [_get_date],
            'result': {'type': 'form',
                'arch': _followup_wizard_date_form,
                'fields': _followup_wizard_date_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('next', 'Continue'),
                ]
            },
        },
        'next': {
            'actions': [_get_partners],
            'result': {'type': 'form',
                'arch': _followup_wizard_all_form,
                'fields': _followup_wizard_all_fields,
                'state': [
                    ('end','Cancel'),
                    ('print','Print Follow Ups'),
                    ('sendmail','Send Mail')
                ]
            },
        },
        'print': {
            'actions': [_update_partners],
            'result': {'type': 'print',
                'report':'account_followup.followup.print',
                'state':'end'},
        },
        'sendmail': {
            'actions': [_sendmail],
            'result': {'type': 'form',
                'arch': form,
                'fields': fields,
                'state':[('end','Ok')]},
        },
    }

followup_all_print('account_followup.followup.print.all')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

