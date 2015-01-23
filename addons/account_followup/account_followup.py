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

    @api.model
    def _get_default_template(self):
        try:
            return self.env['ir.model.data'].xmlid_to_res_id('account_followup.email_template_account_followup_default', raise_if_not_found=True)
        except ValueError:
            return False

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
    email_template_id = fields.Many2one('mail.template', 'Email Template', ondelete='set null', default='_get_default_template')

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

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(res_partner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form' and self.env.context.get('Followupfirst'):
            doc = etree.XML(res['arch'], parser=None, base_url=None)
            first_node = doc.xpath("//page[@name='followup_tab']")
            root = first_node[0].getparent()
            root.insert(0, first_node[0])
            res['arch'] = etree.tostring(doc, encoding="utf-8")
        return res

    @api.one
    @api.depends('unreconciled_aml_ids', 'unreconciled_aml_ids.followup_line_id', 'unreconciled_aml_ids.followup_date', 'unreconciled_aml_ids.blocked')
    def _get_latest(self, company_id=None):
        if company_id == None:
            company = self.env.user.company_id
        else:
            company = self.env['res.company'].browse(company_id)

        amls = self.unreconciled_aml_ids
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
                latest_days_without_lit = aml.followup_line_id.delay
                latest_level_without_lit = aml.followup_line_id.id
        self.latest_followup_date = latest_date
        self.latest_followup_level_id = latest_level
        self.latest_followup_level_id_without_lit = latest_level_without_lit

    @api.one
    def do_partner_manual_action(self):
        #Check action: check if the action was not empty, if not add
        action_text = ""
        if self.payment_next_action:
            action_text = (self.payment_next_action or '') + "\n" + (self.latest_followup_level_id_without_lit.manual_action_note or '')
        else:
            action_text = self.latest_followup_level_id_without_lit.manual_action_note or ''

        #Check date: only change when it did not exist already
        action_date = self.payment_next_action_date or fields.date.context_today(self)

        # Check responsible: if partner has not got a responsible already, take from follow-up
        responsible_id = False
        if self.payment_responsible_id:
            responsible_id = self.payment_responsible_id.id
        else:
            p = self.latest_followup_level_id_without_lit.manual_action_responsible_id
            responsible_id = p and p.id or False
        self.write({'payment_next_action_date': action_date,
                    'payment_next_action': action_text,
                    'payment_responsible_id': responsible_id})

    def do_partner_print(self, wizard_partner_ids, form):
        #wizard_partner_ids are ids from special view, not from res.partner
        if not wizard_partner_ids:
            return {}
        form['partner_ids'] = wizard_partner_ids
        data = {
            'ids': wizard_partner_ids,
            'model': 'account_followup.followup',
            'form': form
        }
        return self.env['report'].get_action(self.browse([]), 'account_followup.report_followup', data=data)

    @api.multi
    def do_partner_mail(self):
        self = self.with_context(followup=True)
        #partner_ids are res.partner ids
        # If not defined by latest follow-up level, it will be the default template if it can find it
        unknown_mails = 0
        for partner in self:
            if partner.email and partner.email.strip():
                level = partner.latest_followup_level_id_without_lit
                if level and level.send_email and level.email_template_id and level.email_template_id.id:
                    level.email_template_id.send_mail(partner.id)
                else:
                    mail_template_id = self.env['ir.model.data'].xmlid_to_object('account_followup.email_template_account_followup_default')
                    mail_template_id.send_mail(partner.id)
            else:
                unknown_mails = unknown_mails + 1
                action_text = _("Email not sent because of email address of partner not filled in")
                if partner.payment_next_action_date:
                    payment_action_date = min(fields.date.context_today(self), partner.payment_next_action_date)
                else:
                    payment_action_date = fields.date.context_today(self)
                if partner.payment_next_action:
                    payment_next_action = partner.payment_next_action + " \n " + action_text
                else:
                    payment_next_action = action_text
                self.write({'payment_next_action_date': payment_action_date, 'payment_next_action': payment_next_action})
        return unknown_mails

    @api.multi
    def get_followup_table_html(self):
        """ Build the html tables to be included in emails send to partners,
            when reminding them their overdue invoices.
            :param ids: [id] of the partner for whom we are building the tables
            :rtype: string
        """
        from report import account_followup_print

        self.ensure_one()

        #Set the language to use = the partner language
        self = self.with_context(lang=self.lang)
        followup_table = ''
        if self.unreconciled_aml_ids:
            company = self.env.user.company_id
            current_date = fields.Date.context_today(self)
            rml_parse = account_followup_print.report_rappel(self.env.cr, self.env.uid, "followup_rml_parser", context=self.env.context)
            final_res = rml_parse._lines_get_with_partner(self, company.id)

            for currency_dict in final_res:
                currency = currency_dict.get('line', [{'currency_id': company.currency_id}])[0]['currency_id']
                followup_table += '''
                <table border="2" width=100%%>
                <tr>
                    <td>''' + _("Invoice Date") + '''</td>
                    <td>''' + _("Description") + '''</td>
                    <td>''' + _("Reference") + '''</td>
                    <td>''' + _("Due Date") + '''</td>
                    <td>''' + _("Amount") + " (%s)" % (currency.symbol) + '''</td>
                    <td>''' + _("Lit.") + '''</td>
                </tr>
                '''
                total = 0
                for aml in currency_dict['line']:
                    block = aml['blocked'] and 'X' or ' '
                    total += aml['balance']
                    strbegin = "<TD>"
                    strend = "</TD>"
                    date = aml['date_maturity'] or aml['date']
                    if date <= current_date and aml['balance'] > 0:
                        strbegin = "<TD><B>"
                        strend = "</B></TD>"
                    followup_table +="<TR>" + strbegin + str(aml['date']) + strend + strbegin + aml['name'] + strend + strbegin + (aml['ref'] or '') + strend + strbegin + str(date) + strend + strbegin + str(aml['balance']) + strend + strbegin + block + strend + "</TR>"

                total = reduce(lambda x, y: x+y['balance'], currency_dict['line'], 0.00)

                total = rml_parse.formatLang(total, dp='Account', currency_obj=currency)
                followup_table += '''<tr> </tr>
                                </table>
                                <center>''' + _("Amount due") + ''' : %s </center>''' % (total)
        return followup_table

    @api.multi
    def write(self, vals):
        if vals.get("payment_responsible_id", False):
            for part in self:
                if part.payment_responsible_id != vals["payment_responsible_id"]:
                    #Find partner_id of user put as responsible
                    responsible_partner_id = self.env["res.users"].browse(vals['payment_responsible_id']).partner_id.id
                    self.env['mail.thread'].browse([]).message_post(
                        body=_("You became responsible to do the next action for the payment follow-up of") + " <b><a href='#id=" + str(part.id) + "&view_type=form&model=res.partner'> " + part.name + " </a></b>",
                        type='comment',
                        subtype="mail.mt_comment",
                        model='res.partner', res_id=part.id,
                        partner_ids=[responsible_partner_id]
                    )
        return super(res_partner, self).write(vals)

    @api.multi
    def action_done(self):
        return self.write({'payment_next_action_date': False, 'payment_next_action':'', 'payment_responsible_id': False})

    @api.multi
    def do_button_print(self):
        self.ensure_one()
        company_id = self.env.user.company_id
        #search if the partner has accounting entries to print. If not, it may not be present in the
        #psql view the report is based on, so we need to stop the user here.
        if not self.env['account.move.line'].search([
                                                       ('partner_id', '=', self.id),
                                                       ('account_id.internal_type', '=', 'receivable'),
                                                       ('reconciled', '=', False),
                                                       ('company_id', '=', company_id.id),
                                                    ]):
            raise Warning(_("The partner does not have any accounting entries to print in the overdue report for the current company."))
        self.message_post(body=_('Printed overdue payments report'))
        #build the id of this partner in the psql view. Could be replaced by a search with [('company_id', '=', company_id),('partner_id', '=', ids[0])]
        wizard_partner_ids = [self.id * 10000 + company_id.id]
        followup_ids = self.env['account_followup.followup'].search([('company_id', '=', company_id.id)])
        if not followup_ids:
            raise Warning(_("There is no followup plan defined for the current company."))
        data = {
            'date': fields.Date.today(),
            'followup_id': followup_ids[0].id,
        }
        #call the print overdue report on this partner
        return self.do_partner_print(wizard_partner_ids, data)

    @api.one
    @api.depends('depends_field', 'unreconciled_aml_ids.date_maturity', 'unreconciled_aml_ids.date', 'unreconciled_aml_ids.result')
    def _get_amounts_and_date(self):
        '''
        Function that computes values for the followup functional fields. Note that 'payment_amount_due'
        is similar to 'credit' field on res.partner except it filters on user's company.
        '''
        company_id = self.env.user.company_id
        current_date = fields.Date.context_today(self)
        worst_due_date = False
        amount_due = amount_overdue = 0.0
        for aml in self.unreconciled_aml_ids:
            if (aml.company_id == company_id):
                date_maturity = aml.date_maturity or aml.date
                if not worst_due_date or date_maturity < worst_due_date:
                    worst_due_date = date_maturity
                amount_due += aml.result
                if (date_maturity <= current_date):
                    amount_overdue += aml.result
        self.payment_amount_due = amount_due
        self.payment_amount_overdue = amount_overdue
        self.payment_earliest_due_date = worst_due_date
        self.depends_field = self.depends_field + 1

    @api.model
    def _get_followup_overdue_query(self, operator, value, overdue_only=False):
        '''
        This function is used to build the query and arguments to use when making a search on functional fields
            * payment_amount_due
            * payment_amount_overdue
        Basically, the query is exactly the same except that for overdue there is an extra clause in the WHERE.

        :param args: arguments given to the search in the usual domain notation (list of tuples)
        :param overdue_only: option to add the extra argument to filter on overdue accounting entries or not
        :returns: a tuple with
            * the query to execute as first element
            * the arguments for the execution of this query
        :rtype: (string, [])
        '''
        company_id = self.env.user.company_id
        having_where_clause = 'SUM(bal2) %s %%s' % operator
        having_values = [value]
        query = self.env['account.move.line']._query_get()
        overdue_only_str = overdue_only and 'AND date_maturity <= NOW()' or ''
        return ('''SELECT pid AS partner_id, SUM(bal2) FROM
                    (SELECT CASE WHEN bal IS NOT NULL THEN bal
                    ELSE 0.0 END AS bal2, p.id as pid FROM
                    (SELECT (debit-credit) AS bal, partner_id
                    FROM account_move_line l
                    WHERE account_id IN
                            (SELECT a.id FROM account_account a
                                LEFT JOIN account_account_type act ON (a.user_type=act.id)
                            WHERE act.type=\'receivable\' AND deprecated='f')
                    ''' + overdue_only_str + '''
                    AND reconciled IS FALSE
                    AND company_id = %s
                    ''' + query + ''') AS l
                    RIGHT JOIN res_partner p
                    ON p.id = partner_id ) AS pl
                    GROUP BY pid HAVING ''' + having_where_clause, [company_id.id] + having_values)

    def _payment_overdue_search(self, operator, value):
        query, query_args = self._get_followup_overdue_query(operator, value, overdue_only=True)
        self.env.cr.execute(query, query_args)
        res = self.env.cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    def _payment_earliest_date_search(self, operator, value):
        company_id = self.env.user.company_id
        having_where_clause = ' AND (MIN(l.date_maturity) %s %%s)' % operator
        having_values = [value]
        query = self.env['account.move.line']._query_get()
        self.env.cr.execute('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT a.id FROM account_account a'\
                        'LEFT JOIN account_account_type act ON (a.user_type=act.id)'\
                        'WHERE act.type=\'receivable\' AND deprecated=False) '\
                    'AND l.company_id = %s '
                    'AND reconciled IS FALSE '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+ having_where_clause,
                     [company_id.id] + having_values)
        res = self.env.cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    def _payment_due_search(self, operator, value):
        query, query_args = self._get_followup_overdue_query(operator, value, overdue_only=False)
        self.env.cr.execute(query, query_args)
        res = self.env.cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    def get_partners_in_need_of_action(self):
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
    unreconciled_aml_ids = fields.One2many('account.move.line', 'partner_id', domain=['&', ('reconciled', '=', False), '&',
                                           ('account_id.deprecated', '=', False), '&', ('account_id.internal_type', '=', 'receivable')])
    latest_followup_date = fields.Date(compute='_get_latest', string="Latest Follow-up Date",
                                       help="Latest date that the follow-up level of the partner was changed",
                                       store=False, company_dependent=True)
    latest_followup_level_id = fields.Many2one('account_followup.followup.line', compute='_get_latest',
                                               help="The maximum follow-up level", string="Latest Follow-up Level",
                                               store=True, company_dependent=True)
    latest_followup_level_id_without_lit = fields.Many2one('account_followup.followup.line', compute='_get_latest',
        string="Latest Follow-up Level without litigation",
        help="The maximum follow-up level without taking into account the account move lines with litigation",
        store=True, company_dependent=True)
    payment_amount_due = fields.Float(compute='_get_amounts_and_date', string="Amount Due",
                                      store=False, search='_payment_due_search', company_dependent=True)
    payment_amount_overdue = fields.Float(compute='_get_amounts_and_date', string="Amount Overdue",
                                          store=False, search='_payment_overdue_search', company_dependent=True)
    payment_earliest_due_date = fields.Date(compute='_get_amounts_and_date', string="Worst Due Date", store=False,
                                            search='_payment_earliest_date_search', company_dependent=True)
    depends_field = fields.Integer(default=0)
    trust = fields.Selection([('good', 'Good Debtor'), ('normal', 'Normal Debtor'), ('bad', 'Bad Debtor')], string='Degree of trust you have in this debtor', default='normal', company_dependent=True)


class account_config_settings(models.TransientModel):
    _name = 'account.config.settings'
    _inherit = 'account.config.settings'

    def open_followup_level_form(self):
        res_ids = self.env['account_followup.followup'].search([])

        return {
                 'type': 'ir.actions.act_window',
                 'name': 'Payment Follow-ups',
                 'res_model': 'account_followup.followup',
                 'res_id': res_ids and res_ids[0] or False,
                 'view_mode': 'form,tree',
         }
