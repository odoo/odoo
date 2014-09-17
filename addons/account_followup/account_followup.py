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

from openerp import api
from openerp.osv import fields, osv
from lxml import etree
from openerp.tools.translate import _

class followup(osv.osv):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'
    _columns = {
        'followup_line': fields.one2many('account_followup.followup.line', 'followup_id', 'Follow-up', copy=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'name': fields.related('company_id', 'name', string = "Name", readonly=True, type="char"),
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account_followup.followup', context=c),
    }
    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Only one follow-up per company is allowed')] 


class followup_line(osv.osv):

    def _get_default_template(self, cr, uid, ids, context=None):
        try:
            return self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_followup', 'email_template_account_followup_default')[1]
        except ValueError:
            return False

    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    _columns = {
        'name': fields.char('Follow-Up Action', required=True),
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
        'send_letter': True,
        'manual_action':False,
        'description': """
        Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. Do not hesitate to contact our accounting department.

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


class res_partner(osv.osv):

    def fields_view_get(self, cr, uid, view_id=None, view_type=None, context=None, toolbar=False, submenu=False):
        res = super(res_partner, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context,
                                                       toolbar=toolbar, submenu=submenu)
        context = context or {}
        if view_type == 'form' and context.get('Followupfirst'):
            doc = etree.XML(res['arch'], parser=None, base_url=None)
            first_node = doc.xpath("//page[@name='followup_tab']")
            root = first_node[0].getparent()
            root.insert(0, first_node[0])
            res['arch'] = etree.tostring(doc, encoding="utf-8")
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

    @api.cr_uid_ids_context
    def do_partner_manual_action(self, cr, uid, partner_ids, context=None): 
        #partner_ids -> res.partner
        for partner in self.browse(cr, uid, partner_ids, context=context):
            #Check action: check if the action was not empty, if not add
            action_text= ""
            if partner.payment_next_action:
                action_text = (partner.payment_next_action or '') + "\n" + (partner.latest_followup_level_id_without_lit.manual_action_note or '')
            else:
                action_text = partner.latest_followup_level_id_without_lit.manual_action_note or ''

            #Check date: only change when it did not exist already
            action_date = partner.payment_next_action_date or fields.date.context_today(self, cr, uid, context=context)

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
             'ids': wizard_partner_ids,
             'model': 'account_followup.followup',
             'form': data
        }
        return self.pool['report'].get_action(cr, uid, [], 'account_followup.report_followup', data=datas, context=context)

    @api.cr_uid_ids_context
    def do_partner_mail(self, cr, uid, partner_ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['followup'] = True
        #partner_ids are res.partner ids
        # If not defined by latest follow-up level, it will be the default template if it can find it
        mtp = self.pool.get('email.template')
        unknown_mails = 0
        for partner in self.browse(cr, uid, partner_ids, context=ctx):
            if partner.email and partner.email.strip():
                level = partner.latest_followup_level_id_without_lit
                if level and level.send_email and level.email_template_id and level.email_template_id.id:
                    mtp.send_mail(cr, uid, level.email_template_id.id, partner.id, context=ctx)
                else:
                    mail_template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 
                                                    'account_followup', 'email_template_account_followup_default')
                    mtp.send_mail(cr, uid, mail_template_id[1], partner.id, context=ctx)
            else:
                unknown_mails = unknown_mails + 1
                action_text = _("Email not sent because of email address of partner not filled in")
                if partner.payment_next_action_date:
                    payment_action_date = min(fields.date.context_today(self, cr, uid, context=ctx), partner.payment_next_action_date)
                else:
                    payment_action_date = fields.date.context_today(self, cr, uid, context=ctx)
                if partner.payment_next_action:
                    payment_next_action = partner.payment_next_action + " \n " + action_text
                else:
                    payment_next_action = action_text
                self.write(cr, uid, [partner.id], {'payment_next_action_date': payment_action_date,
                                                   'payment_next_action': payment_next_action}, context=ctx)
        return unknown_mails

    def get_followup_table_html(self, cr, uid, ids, context=None):
        """ Build the html tables to be included in emails send to partners,
            when reminding them their overdue invoices.
            :param ids: [id] of the partner for whom we are building the tables
            :rtype: string
        """
        from report import account_followup_print

        assert len(ids) == 1
        if context is None:
            context = {}
        partner = self.browse(cr, uid, ids[0], context=context)
        #copy the context to not change global context. Overwrite it because _() looks for the lang in local variable 'context'.
        #Set the language to use = the partner language
        context = dict(context, lang=partner.lang)
        followup_table = ''
        if partner.unreconciled_aml_ids:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            current_date = fields.date.context_today(self, cr, uid, context=context)
            rml_parse = account_followup_print.report_rappel(cr, uid, "followup_rml_parser")
            final_res = rml_parse._lines_get_with_partner(partner, company.id)

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

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get("payment_responsible_id", False):
            for part in self.browse(cr, uid, ids, context=context):
                if part.payment_responsible_id <> vals["payment_responsible_id"]:
                    #Find partner_id of user put as responsible
                    responsible_partner_id = self.pool.get("res.users").browse(cr, uid, vals['payment_responsible_id'], context=context).partner_id.id
                    self.pool.get("mail.thread").message_post(cr, uid, 0, 
                                      body = _("You became responsible to do the next action for the payment follow-up of") + " <b><a href='#id=" + str(part.id) + "&view_type=form&model=res.partner'> " + part.name + " </a></b>",
                                      type = 'comment',
                                      subtype = "mail.mt_comment", context = context,
                                      model = 'res.partner', res_id = part.id, 
                                      partner_ids = [responsible_partner_id])
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def action_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'payment_next_action_date': False, 'payment_next_action':'', 'payment_responsible_id': False}, context=context)

    def do_button_print(self, cr, uid, ids, context=None):
        assert(len(ids) == 1)
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        #search if the partner has accounting entries to print. If not, it may not be present in the
        #psql view the report is based on, so we need to stop the user here.
        if not self.pool.get('account.move.line').search(cr, uid, [
                                                                   ('partner_id', '=', ids[0]),
                                                                   ('account_id.type', '=', 'receivable'),
                                                                   ('reconcile_id', '=', False),
                                                                   ('state', '!=', 'draft'),
                                                                   ('company_id', '=', company_id),
                                                                  ], context=context):
            raise osv.except_osv(_('Error!'),_("The partner does not have any accounting entries to print in the overdue report for the current company."))
        self.message_post(cr, uid, [ids[0]], body=_('Printed overdue payments report'), context=context)
        #build the id of this partner in the psql view. Could be replaced by a search with [('company_id', '=', company_id),('partner_id', '=', ids[0])]
        wizard_partner_ids = [ids[0] * 10000 + company_id]
        followup_ids = self.pool.get('account_followup.followup').search(cr, uid, [('company_id', '=', company_id)], context=context)
        if not followup_ids:
            raise osv.except_osv(_('Error!'),_("There is no followup plan defined for the current company."))
        data = {
            'date': fields.date.today(),
            'followup_id': followup_ids[0],
        }
        #call the print overdue report on this partner
        return self.do_partner_print(cr, uid, wizard_partner_ids, data, context=context)

    def _get_amounts_and_date(self, cr, uid, ids, name, arg, context=None):
        '''
        Function that computes values for the followup functional fields. Note that 'payment_amount_due'
        is similar to 'credit' field on res.partner except it filters on user's company.
        '''
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        current_date = fields.date.context_today(self, cr, uid, context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            worst_due_date = False
            amount_due = amount_overdue = 0.0
            for aml in partner.unreconciled_aml_ids:
                if (aml.company_id == company):
                    date_maturity = aml.date_maturity or aml.date
                    if not worst_due_date or date_maturity < worst_due_date:
                        worst_due_date = date_maturity
                    amount_due += aml.result
                    if (date_maturity <= current_date):
                        amount_overdue += aml.result
            res[partner.id] = {'payment_amount_due': amount_due, 
                               'payment_amount_overdue': amount_overdue, 
                               'payment_earliest_due_date': worst_due_date}
        return res

    def _get_followup_overdue_query(self, cr, uid, args, overdue_only=False, context=None):
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
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        having_where_clause = ' AND '.join(map(lambda x: '(SUM(bal2) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        overdue_only_str = overdue_only and 'AND date_maturity <= NOW()' or ''
        return ('''SELECT pid AS partner_id, SUM(bal2) FROM
                    (SELECT CASE WHEN bal IS NOT NULL THEN bal
                    ELSE 0.0 END AS bal2, p.id as pid FROM
                    (SELECT (debit-credit) AS bal, partner_id
                    FROM account_move_line l
                    WHERE account_id IN
                            (SELECT id FROM account_account
                            WHERE type=\'receivable\' AND active)
                    ''' + overdue_only_str + '''
                    AND reconcile_id IS NULL
                    AND company_id = %s
                    AND ''' + query + ''') AS l
                    RIGHT JOIN res_partner p
                    ON p.id = partner_id ) AS pl
                    GROUP BY pid HAVING ''' + having_where_clause, [company_id] + having_values)

    def _payment_overdue_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(cr, uid, args, overdue_only=True, context=context)
        cr.execute(query, query_args)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    def _payment_earliest_date_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        having_where_clause = ' AND '.join(map(lambda x: '(MIN(l.date_maturity) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT id FROM account_account '\
                        'WHERE type=\'receivable\' AND active) '\
                    'AND l.company_id = %s '
                    'AND reconcile_id IS NULL '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+ having_where_clause,
                     [company_id] + having_values)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    def _payment_due_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(cr, uid, args, overdue_only=False, context=context)
        cr.execute(query, query_args)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    def _get_partners(self, cr, uid, ids, context=None):
        #this function search for the partners linked to all account.move.line 'ids' that have been changed
        partners = set()
        for aml in self.browse(cr, uid, ids, context=context):
            if aml.partner_id:
                partners.add(aml.partner_id.id)
        return list(partners)

    _inherit = "res.partner"
    _columns = {
        'payment_responsible_id':fields.many2one('res.users', ondelete='set null', string='Follow-up Responsible', 
                                                 help="Optionally you can assign a user to this field, which will make him responsible for the action.", 
                                                 track_visibility="onchange", copy=False), 
        'payment_note':fields.text('Customer Payment Promise', help="Payment Note", track_visibility="onchange", copy=False),
        'payment_next_action':fields.text('Next Action', copy=False,
                                    help="This is the next action to be taken.  It will automatically be set when the partner gets a follow-up level that requires a manual action. ", 
                                    track_visibility="onchange"), 
        'payment_next_action_date': fields.date('Next Action Date', copy=False,
                                    help="This is when the manual follow-up is needed. "
                                         "The date will be set to the current date when the partner "
                                         "gets a follow-up level that requires a manual action. "
                                         "Can be practical to set manually e.g. to see if he keeps "
                                         "his promises."),
        'unreconciled_aml_ids':fields.one2many('account.move.line', 'partner_id', domain=['&', ('reconcile_id', '=', False), '&', 
                            ('account_id.active','=', True), '&', ('account_id.type', '=', 'receivable'), ('state', '!=', 'draft')]), 
        'latest_followup_date':fields.function(_get_latest, method=True, type='date', string="Latest Follow-up Date", 
                            help="Latest date that the follow-up level of the partner was changed", 
                            store=False, multi="latest"), 
        'latest_followup_level_id':fields.function(_get_latest, method=True, 
            type='many2one', relation='account_followup.followup.line', string="Latest Follow-up Level", 
            help="The maximum follow-up level", 
            store={
                'res.partner': (lambda self, cr, uid, ids, c: ids,[],10),
                'account.move.line': (_get_partners, ['followup_line_id'], 10),
            }, 
            multi="latest"), 
        'latest_followup_level_id_without_lit':fields.function(_get_latest, method=True, 
            type='many2one', relation='account_followup.followup.line', string="Latest Follow-up Level without litigation", 
            help="The maximum follow-up level without taking into account the account move lines with litigation", 
            store={
                'res.partner': (lambda self, cr, uid, ids, c: ids,[],10),
                'account.move.line': (_get_partners, ['followup_line_id'], 10),
            }, 
            multi="latest"),
        'payment_amount_due':fields.function(_get_amounts_and_date, 
                                                 type='float', string="Amount Due",
                                                 store = False, multi="followup", 
                                                 fnct_search=_payment_due_search),
        'payment_amount_overdue':fields.function(_get_amounts_and_date,
                                                 type='float', string="Amount Overdue",
                                                 store = False, multi="followup", 
                                                 fnct_search = _payment_overdue_search),
        'payment_earliest_due_date':fields.function(_get_amounts_and_date,
                                                    type='date',
                                                    string = "Worst Due Date",
                                                    multi="followup",
                                                    fnct_search=_payment_earliest_date_search),
        }


class account_config_settings(osv.TransientModel):
    _name = 'account.config.settings'
    _inherit = 'account.config.settings'
    
    def open_followup_level_form(self, cr, uid, ids, context=None):
        res_ids = self.pool.get('account_followup.followup').search(cr, uid, [], context=context)
        
        return {
                 'type': 'ir.actions.act_window',
                 'name': 'Payment Follow-ups',
                 'res_model': 'account_followup.followup',
                 'res_id': res_ids and res_ids[0] or False,
                 'view_mode': 'form,tree',
         }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
