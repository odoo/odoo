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

from openerp import api, fields, models, _
from openerp.exceptions import Warning
from lxml import etree
import datetime
import time


class followup(models.Model):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'

    followup_line = fields.One2many('account_followup.followup.line', 'followup_id', 'Follow-up', copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account_followup.followup', context=c))
    name = fields.Char(related='company_id.name', readonly=True)

    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Only one follow-up per company is allowed')] 


class followup_line(models.Model):
    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    _order = 'delay'

    name = fields.Char('Follow-Up Action', required=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of follow-up lines.")
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice to wait before sending the reminder.  Could be negative if you want to send a polite alert beforehand.")
    followup_id = fields.Many2one('account_followup.followup', 'Follow Ups', required=True, ondelete="cascade")
    description = fields.Text('Printed Message', translate=True, default="""
        Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. Do not hesitate to contact our accounting department.

Best Regards,
""")
    send_email = fields.Boolean('Send an Email', help="When processing, it will send an email", default=True)
    send_letter = fields.Boolean('Send a Letter', help="When processing, it will print a letter", default=True)
    manual_action = fields.Boolean('Manual Action', help="When processing, it will set the manual action to be taken for that customer. ", default=False)
    manual_action_note = fields.Text('Action To Do', placeholder="e.g. Give a phone call, check with others , ...")
    manual_action_responsible_id = fields.Many2one('res.users', 'Assign a Responsible', ondelete='set null')

    _sql_constraints = [('days_uniq', 'unique(followup_id, delay)', 'Days of the follow-up levels must be different')]

    @api.constrains('description')
    def _check_description(self):
        for line in self:
            if line.description:
                try:
                    line.description % {'partner_name': '', 'date':'', 'user_signature': '', 'company_name': ''}
                except:
                    raise Warning(_('Your description is invalid, use the right legend or %% if you want to use the percent character.'))


class account_move_line(models.Model):
    _inherit = 'account.move.line'

    @api.one
    @api.depends('debit', 'credit')
    def _get_result(self):
        self.result = self.debit - self.credit

    followup_line_id = fields.Many2one('account_followup.followup.line', 'Follow-up Level',
                                       ondelete='restrict') #restrict deletion of the followup line
    followup_date = fields.Date('Latest Follow-up', select=True)
    result = fields.Float(compute='_get_result', method=True, string="Balance") #'balance' field is not the same


class res_partner(models.Model):
    _inherit = "res.partner"

    def get_partners_in_need_of_action_and_update(self):
        company_id = self.env.user.company_id
        context = self.env.context
        cr = self.env.cr
        date = 'date' in context and context['date'] or time.strftime('%Y-%m-%d')

        cr.execute(
            "SELECT l.partner_id, l.followup_line_id, l.date_maturity, l.date, l.id, fl.delay "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
                "LEFT JOIN account_account_type AS act "\
                "ON (a.user_type=act.id) "\
                "LEFT JOIN account_followup_followup_line AS fl "\
                "ON (l.followup_line_id=fl.id) "\
            "WHERE (l.reconciled IS FALSE) "\
                "AND (act.type='receivable') "\
                "AND (l.partner_id is NOT NULL) "\
                "AND (a.deprecated='f') "\
                "AND (l.debit > 0) "\
                "AND (l.company_id = %s) " \
                "AND (l.blocked IS FALSE) " \
            "ORDER BY l.date", (company_id.id,))  #l.blocked added to take litigation into account and it is not necessary to change follow-up level of account move lines without debit
        move_lines = cr.fetchall()
        old = None
        fups = {}
        fup_id = 'followup_id' in context and context['followup_id'] or self.env['account_followup.followup'].search([('company_id', '=', company_id.id)]).id

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

        result = {}

        partners_to_skip = self.env['res.partner'].search([('payment_next_action_date', '>', date)])

        #Fill dictionary of accountmovelines to_update with the partners that need to be updated
        for partner_id, followup_line_id, date_maturity, date, id, delay in move_lines:
            if not partner_id or partner_id in partners_to_skip.ids:
                continue
            if followup_line_id not in fups:
                continue
            if date_maturity:
                if date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                    if partner_id not in result.keys():
                        result.update({partner_id: (fups[followup_line_id][1], delay)})
                    elif result[partner_id][1] < delay:
                        result[partner_id] = (fups[followup_line_id][1], delay)
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                if partner_id not in result.keys():
                    result.update({partner_id: (fups[followup_line_id][1], delay)})
                elif result[partner_id][1] < delay:
                    result[partner_id] = (fups[followup_line_id][1], delay)
        return result

    @api.multi
    def update_next_action(self):
        company_id = self.env.user.company_id
        context = self.env.context
        cr = self.env.cr
        old = None
        fups = {}
        fup_id = 'followup_id' in context and context['followup_id'] or self.env['account_followup.followup'].search([('company_id', '=', company_id.id)]).id
        date = 'date' in context and context['date'] or time.strftime('%Y-%m-%d')

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

        for partner in self:
            for aml in partner.unreconciled_aml_ids:
                followup_line_id = aml.followup_line_id.id or None
                if aml.date_maturity:
                    if aml.date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                        aml.write({'followup_line_id': fups[followup_line_id][1], 'followup_date': date})
                elif aml.date and aml.date <= fups[followup_line_id.id][0].strftime('%Y-%m-%d'):
                    aml.write({'followup_line_id': fups[followup_line_id][1], 'followup_date': date})

    payment_responsible_id = fields.Many2one('res.users', ondelete='set null', string='Follow-up Responsible',
                                             help="Optionally you can assign a user to this field, which will make him responsible for the action.",
                                             track_visibility="onchange", copy=False, company_dependent=True)
    payment_note = fields.Text('Customer Payment Promise', help="Payment Note", track_visibility="onchange", copy=False, company_dependent=True)
    trust = fields.Selection([('good', 'Good Debtor'), ('normal', 'Normal Debtor'), ('bad', 'Bad Debtor')], string='Degree of trust you have in this debtor', default='normal', company_dependent=True)


class account_config_settings(models.TransientModel):
    _name = 'account.config.settings'
    _inherit = 'account.config.settings'

    @api.multi
    def open_followup_level_form(self):
        res_ids = self.env['account_followup.followup'].search([])

        return {
                 'type': 'ir.actions.act_window',
                 'name': 'Payment Follow-ups',
                 'res_model': 'account_followup.followup',
                 'res_id': res_ids and res_ids.ids[0] or False,
                 'view_mode': 'form,tree',
         }
