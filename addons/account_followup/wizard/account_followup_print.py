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

from openerp import tools
from openerp import api, fields, models, _

class account_followup_stat_by_partner(models.Model):
    _name = "account_followup.stat.by.partner"
    _description = "Follow-up Statistics by Partner"
    _rec_name = 'partner_id'
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    date_move = fields.Date('First move', readonly=True)
    date_move_last = fields.Date('Last move', readonly=True)
    date_followup = fields.Date('Latest follow-up', readonly=True)
    max_followup_id = fields.Many2one('account_followup.followup.line',
                                    'Max Follow Up Level', readonly=True, ondelete="cascade")
    balance = fields.Float('Balance', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)

    _depends = {
        'account.move.line': [
            'account_id', 'company_id', 'credit', 'date', 'debit',
            'followup_date', 'followup_line_id', 'partner_id', 'reconciled',
        ],
        'account.account': ['deprecated', 'user_type'],
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_followup_stat_by_partner')
        # Here we don't have other choice but to create a virtual ID based on the concatenation
        # of the partner_id and the company_id, because if a partner is shared between 2 companies,
        # we want to see 2 lines for him in this table. It means that both company should be able
        # to send him follow-ups separately . An assumption that the number of companies will not
        # reach 10 000 records is made, what should be enough for a time.
        cr.execute("""
            create view account_followup_stat_by_partner as (
                SELECT
                    l.partner_id * 10000::bigint + l.company_id as id,
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
                    LEFT JOIN account_account_type act ON (a.user_type = act.id)
                WHERE
                    a.deprecated='f' AND
                    act.type = 'receivable' AND
                    l.reconciled is FALSE AND
                    l.partner_id IS NOT NULL
                    GROUP BY
                    l.partner_id, l.company_id
            )""")


class account_followup_sending_results(models.TransientModel):

    @api.multi
    def do_report(self):
        return self.env.context.get('report_data')

    @api.multi
    def do_done(self):
        return {}

    def _get_description(self):
        return self.env.context.get('description')

    def _get_need_printing(self):
        return self.env.context.get('needprinting')

    _name = 'account_followup.sending.results'
    _description = 'Results from the sending of the different letters and emails'

    description = fields.Text("Description", readonly=True, default=_get_description)
    needprinting = fields.Boolean("Needs Printing", default=_get_need_printing)


class account_followup_print(models.TransientModel):
    _name = 'account_followup.print'
    _description = 'Print Follow-up & Send Mail to Customers'

    @api.model
    def _get_followup(self):
        if self.env.context.get('active_model', 'ir.ui.menu') == 'account_followup.followup':
            return self.env.context.get('active_id', False)
        company_id = self.env.user.company_id
        followp_id = self.env['account_followup.followup'].search([('company_id', '=', company_id.id)])
        return followp_id and followp_id[0] or False

    date = fields.Date('Follow-up Sending Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d'),
                       help="This field allow you to select a forecast date to plan your follow-ups")
    followup_id = fields.Many2one('account_followup.followup', 'Follow-Up', required=True, readonly=True, default=_get_followup)
    partner_ids = fields.Many2many('account_followup.stat.by.partner', 'partner_stat_rel',
                                   'osv_memory_id', 'partner_id', 'Partners', required=True)
    company_id = fields.Many2one(related='followup_id.company_id', store=True, readonly=True)
    email_conf = fields.Boolean('Send Email Confirmation')
    email_subject = fields.Char('Email Subject', size=64, default=_('Invoices Reminder'))
    partner_lang = fields.Boolean('Send Email in Partner Language', default=True,
                                  help='Do not change message text, if you want to send email in partner language, or configure from company')
    email_body = fields.Text('Email Body', default="")
    summary = fields.Text('Summary', readonly=True)
    test_print = fields.Boolean('Test Print', help='Check if you want to print follow-ups without changing follow-up level.')

    def process_partners(self, partner_ids, data):
        partner_ids_to_print = []
        nbmanuals = 0
        manuals = {}
        nbmails = 0
        nbunknownmails = 0
        nbprints = 0
        resulttext = " "
        for partner in partner_ids:
            if partner.max_followup_id.manual_action:
                partner.partner_id.do_partner_manual_action()
                nbmanuals = nbmanuals + 1
                key = partner.partner_id.payment_responsible_id.name or _("Anybody")
                if not key in manuals.keys():
                    manuals[key]= 1
                else:
                    manuals[key] = manuals[key] + 1
            if partner.max_followup_id.send_email:
                nbunknownmails += partner.partner_id.do_partner_mail()
                nbmails += 1
            if partner.max_followup_id.send_letter:
                partner_ids_to_print.append(partner.id)
                nbprints += 1
                message = "%s<I> %s </I>%s" % (_("Follow-up letter of "), partner.partner_id.latest_followup_level_id_without_lit.name, _(" will be sent"))
                partner.partner_id.message_post(body=message)
        if nbunknownmails == 0:
            resulttext += str(nbmails) + _(" email(s) sent")
        else:
            resulttext += str(nbmails) + _(" email(s) should have been sent, but ") + str(nbunknownmails) + _(" had unknown email address(es)") + "\n <BR/> "
        resulttext += "<BR/>" + str(nbprints) + _(" letter(s) in report") + " \n <BR/>" + str(nbmanuals) + _(" manual action(s) assigned:")
        needprinting = False
        if nbprints > 0:
            needprinting = True
        resulttext += "<p align=\"center\">"
        for item in manuals:
            resulttext = resulttext + "<li>" + item + ":" + str(manuals[item]) +  "\n </li>"
        resulttext += "</p>"
        result = {}
        action = self.env['res.partner'].do_partner_print(partner_ids_to_print, data)
        result['needprinting'] = needprinting
        result['resulttext'] = resulttext
        result['action'] = action or {}
        return result

    def do_update_followup_level(self, to_update, partner_list, date):
        #update the follow-up level on account.move.line
        for id in to_update.keys():
            if to_update[id]['partner_id'] in partner_list:
                self.env['account.move.line'].browse([int(id)]).write({'followup_line_id': to_update[id]['level'], 'followup_date': date})


    def clear_manual_actions(self, partner_ids):
        # Partnerlist is list to exclude
        # Will clear the actions of partners that have no due payments anymore
        partner_list_ids = [partner.partner_id.id for partner in partner_ids]
        partners = self.env['res.partner'].search([('id', 'not in', partner_list_ids), '|', ('payment_responsible_id', '!=', False), ('payment_next_action_date', '!=', False)])

        partners_to_clear = self.env['res.partner']
        for part in partners:
            if not part.unreconciled_aml_ids:
                partners_to_clear = partners_to_clear | part.id
        partners_to_clear.action_done()
        return len(partners_to_clear)

    @api.multi
    def do_process(self):
        #Get partners
        tmp = self._get_partners_followp()
        partner_list = tmp['partner_ids']
        to_update = tmp['to_update']
        date = self[0].date
        data = self.read()[0]
        data['followup_id'] = data['followup_id'][0]

        #Update partners
        self.do_update_followup_level(to_update, partner_list, date)
        #process the partners (send mails...)
        restot = self.process_partners(partner_list, data)
        #clear the manual actions if nothing is due anymore
        nbactionscleared = self.clear_manual_actions(partner_list)
        if nbactionscleared > 0:
            restot['resulttext'] = restot['resulttext'] + "<li>" + _("%s partners have no credits and as such the action is cleared") %(str(nbactionscleared)) + "</li>"
        #return the next action
        mod_obj = self.env['ir.model.data']
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'),('name', '=', 'view_account_followup_sending_results')])
        resource_id = model_data_ids[0].res_id
        return {
            'name': _('Send Letters and Emails: Actions Summary'),
            'view_type': 'form',
            'context': self.with_context(description=restot['resulttext'], needprinting=restot['needprinting'], report_data=restot['action']).env.context,
            'view_mode': 'tree,form',
            'res_model': 'account_followup.sending.results',
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            }

    def _get_msg(self):
        return self.env.user.company_id.follow_up_msg

    def _get_partners_followp(self):
        self = self[0]
        company_id = self.company_id
        context = self.env.context
        cr = self.env.cr

        cr.execute(
            "SELECT l.partner_id, l.followup_line_id,l.date_maturity, l.date, l.id "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
                "LEFT JOIN account_account_type AS act "\
                "ON (a.user_type=act.id) "\
            "WHERE (l.reconciled IS FALSE) "\
                "AND (act.type='receivable') "\
                "AND (l.partner_id is NOT NULL) "\
                "AND (a.deprecated='f') "\
                "AND (l.debit > 0) "\
                "AND (l.company_id = %s) " \
                "AND (l.blocked = False)" \
            "ORDER BY l.date", (company_id.id,))  #l.blocked added to take litigation into account and it is not necessary to change follow-up level of account move lines without debit
        move_lines = cr.fetchall()
        old = None
        fups = {}
        fup_id = 'followup_id' in context and context['followup_id'] or self.followup_id.id
        date = 'date' in context and context['date'] or self.date

        current_date = datetime.date(*time.strptime(date, '%Y-%m-%d')[:3])
        cr.execute(
            "SELECT * "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY delay", (fup_id,))

        #Create dictionary of tuples where first element is the date to compare with the due date and second element is the id of the next level
        for result in cr.dictfetchall():
            delay = datetime.timedelta(days=result['delay'])
            fups[old] = (current_date - delay, result['id'])
            old = result['id']

        partner_list = self.browse([])
        to_update = {}

        #Fill dictionary of accountmovelines to_update with the partners that need to be updated
        for partner_id, followup_line_id, date_maturity, date, id in move_lines:
            if not partner_id:
                continue
            if followup_line_id not in fups:
                continue
            stat_line_id = partner_id * 10000 + company_id.id
            if date_maturity:
                if date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                    if stat_line_id not in partner_list.ids:
                        partner_list = partner_list | stat_line_id
                    to_update[str(id)] = {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                if stat_line_id not in partner_list:
                    partner_list = partner_list | stat_line_id
                to_update[str(id)] = {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
        return {'partner_ids': partner_list, 'to_update': to_update}
