# -*- coding: utf-8 -*-

import time
from datetime import datetime

from openerp import workflow
from openerp import models, fields, api, _
from openerp.exceptions import Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.report import report_sxw


class account_move_line(models.Model):
    _name = "account.move.line"
    _description = "Journal Items"
    _order = "date desc, id desc"

    @api.model
    def _query_get(self, obj='l'):
        fiscalyear_obj = self.env['account.fiscalyear']
        fiscalperiod_obj = self.env['account.period']
        account_obj = self.env['account.account']
        fiscalyear_ids = []
        context = dict(self._context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        if context.get('company_id', False):
            company_clause = " AND " +obj+".company_id = %s" % context.get('company_id', False)
        if not context.get('fiscalyear', False):
            if context.get('all_fiscalyear', False):
                #this option is needed by the aged balance report because otherwise, if we search only the draft ones, an open invoice of a closed fiscalyear won't be displayed
                fiscalyear_ids = fiscalyear_obj.search([]).ids
            else:
                fiscalyear_ids = fiscalyear_obj.search([('state', '=', 'draft')]).ids
        else:
            #for initial balance as well as for normal query, we check only the selected FY because the best practice is to generate the FY opening entries
            fiscalyear_ids = [context['fiscalyear']]

        fiscalyear_clause = (','.join([str(x) for x in fiscalyear_ids])) or '0'
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from', False) and context.get('date_to', False):
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date < '" +context['date_from']+"')"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date >= '" +context['date_from']+"' AND date <= '"+context['date_to']+"')"

        if state:
            if state.lower() not in ['all']:
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM account_move WHERE account_move.state = '"+state+"')"
        if context.get('period_from', False) and context.get('period_to', False) and not context.get('periods', False):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(context['period_from']).company_id.id
                first_period = fiscalperiod_obj.search([('company_id', '=', period_company_id)], order='date_start', limit=1)
                context['periods'] = fiscalperiod_obj.build_ctx_periods(first_period.id, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(context['period_from'], context['period_to'])
        if context.get('periods', False):
            if initial_bal:
                query = obj+".state != 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s)) %s %s" % (fiscalyear_clause, where_move_state, where_move_lines_by_date)
                periods = fiscalperiod_obj.search([('id', 'in', context['periods'])], order='date_start', limit=1)
                if periods:
                    ids = ','.join([str(x) for x in context['periods']])
                    query = obj+".state != 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s) AND date_start <= '%s' AND id NOT IN (%s)) %s %s" % (fiscalyear_clause, periods.date_start, ids, where_move_state, where_move_lines_by_date)
            else:
                ids = ','.join([str(x) for x in context['periods']])
                query = obj+".state != 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s) AND id IN (%s)) %s %s" % (fiscalyear_clause, ids, where_move_state, where_move_lines_by_date)
        else:
            query = obj+".state != 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s)) %s %s" % (fiscalyear_clause, where_move_state, where_move_lines_by_date)

        if initial_bal and not context.get('periods', False) and not where_move_lines_by_date:
            #we didn't pass any filter in the context, and the initial balance can't be computed using only the fiscalyear otherwise entries will be summed twice
            #so we have to invalidate this query
            raise Warning(_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))


        if context.get('journal_ids', False):
            query += ' AND '+obj+'.journal_id IN (%s)' % ','.join(map(str, context['journal_ids']))

        if context.get('chart_account_id', False):
            child_ids = account_obj.browse(context['chart_account_id'])._get_children_and_consol()
            query += ' AND '+obj+'.account_id IN (%s)' % ','.join(map(str, child_ids))

        query += company_clause
        return query

    @api.multi
    def _amount_residual(self):
        """
           This function returns the residual amount on a receivable or payable account.move.line.
           By default, it returns an amount in the currency of this journal entry (maybe different
           of the company currency), but if you pass 'residual_in_company_currency' = True in the
           context then the returned amount will be in company currency.
        """
        context = dict(self._context or {})
        for move_line in self:
            move_line.amount_residual = 0.0
            move_line.amount_residual_currency = 0.0

            if move_line.reconcile_id:
                continue
            if not move_line.account_id.reconcile:
                #this function does not suport to be used on move lines not related to a reconcilable account
                continue

            if move_line.currency_id:
                move_line_total = move_line.amount_currency
                sign = move_line.amount_currency < 0 and -1 or 1
            else:
                move_line_total = move_line.debit - move_line.credit
                sign = (move_line.debit - move_line.credit) < 0 and -1 or 1
            line_total_in_company_currency =  move_line.debit - move_line.credit
            context_unreconciled = context.copy()
            if move_line.reconcile_partial_id:
                for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                    if payment_line.id == move_line.id:
                        continue
                    if payment_line.currency_id and move_line.currency_id and payment_line.currency_id.id == move_line.currency_id.id:
                            move_line_total += payment_line.amount_currency
                    else:
                        if move_line.currency_id:
                            context_unreconciled.update({'date': payment_line.date})
                            amount_in_foreign_currency = move_line.company_id.currency_id.with_context(context_unreconciled).compute(
                                                                            move_line.currency_id.id, 
                                                                            (payment_line.debit - payment_line.credit), round=False)
                            move_line_total += amount_in_foreign_currency
                        else:
                            move_line_total += (payment_line.debit - payment_line.credit)
                    line_total_in_company_currency += (payment_line.debit - payment_line.credit)

            result = move_line_total
            move_line.amount_residual_currency =  sign * (move_line.currency_id and move_line.currency_id.round(result) or result)
            move_line.amount_residual = sign * line_total_in_company_currency

    @api.model
    def _prepare_analytic_line(self, obj_line):
        """
        Prepare the values given at the create() of account.analytic.line upon the validation of a journal item having
        an analytic account. This method is intended to be extended in other modules.

        :param obj_line: browse record of the account.move.line that triggered the analytic line creation
        """
        return {'name': obj_line.name,
                'date': obj_line.date,
                'account_id': obj_line.analytic_account_id.id,
                'unit_amount': obj_line.quantity,
                'product_id': obj_line.product_id and obj_line.product_id.id or False,
                'product_uom_id': obj_line.product_uom_id and obj_line.product_uom_id.id or False,
                'amount': (obj_line.credit or  0.0) - (obj_line.debit or 0.0),
                'general_account_id': obj_line.account_id.id,
                'journal_id': obj_line.journal_id.analytic_journal_id.id,
                'ref': obj_line.ref,
                'move_id': obj_line.id,
                'user_id': self._uid,
               }

    @api.multi
    def create_analytic_lines(self):
        for obj_line in self:
            if obj_line.analytic_account_id:
                if not obj_line.journal_id.analytic_journal_id:
                    raise Warning(_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name, ))
                if obj_line.analytic_lines:
                    obj_line.analytic_lines.unlink()
                vals_line = obj_line._prepare_analytic_line()
                self.env['account.analytic.line'].create(vals_line)

    @api.one
    def on_create_write(self):
        if not self:
            return []
        return map(lambda x: x.id, self.move_id.line_id)

    @api.multi
    def _balance(self):
        context = dict(self._context or {})
        context['initital_bal'] = True
        sql = """SELECT l1.id, COALESCE(SUM(l2.debit-l2.credit), 0)
                    FROM account_move_line l1 LEFT JOIN account_move_line l2
                    ON (l1.account_id = l2.account_id
                      AND l2.id <= l1.id
                      AND """ + \
                self.with_context(context)._query_get(obj='l2') + \
                ") WHERE l1.id IN %s GROUP BY l1.id"

        self._cr.execute(sql, [tuple(self.ids)])
        return dict(self._cr.fetchall())

    @api.multi
    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            if line.ref:
                result.append((line.id, (line.move_id.name or '') + '(' + line.ref + ')'))
            else:
                result.append((line.id, line.move_id.name))
        return result

    @api.multi
    def _balance_search(self, args, domain=None):
        result = []
        if args:
            where = ' AND '.join(map(lambda x: '(abs(sum(debit-credit))'+x[1]+str(x[2])+')',args))
            self._cr.execute('SELECT id, SUM(debit-credit) FROM account_move_line \
                         GROUP BY id, debit, credit having '+where)
            data = self._cr.fetchall()
            if data:
                result = [('id', 'in', [x[0] for x in data])]
            else:
                result = [('id', '=', '0')]
        return result

    @api.multi
    @api.depends('reconcile_id','reconcile_partial_id')
    def _get_reconcile(self):
        for line in self:
            if line.reconcile_id:
                line.reconcile_ref = str(line.reconcile_id.name)
            elif line.reconcile_partial_id:
                line.reconcile_ref = str(line.reconcile_partial_id.name)
            # To get rid of Error: Field account.move.line.reconcile_ref is accessed before being computed.
            else:
                line.reconcile_ref = False

    name = fields.Char(string='Name', required=True)
    quantity = fields.Float(string='Quantity', digits=(16,2), 
        help="The optional quantity expressed by this line, eg: number of product sold. "\
        "The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Float(string='Debit', digits=dp.get_precision('Account'), default=0.0)
    credit = fields.Float(string='Credit', digits=dp.get_precision('Account'), default=0.0)
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
        ondelete="cascade", domain=[('type', '!=', 'view'), ('type', '!=', 'closed'), ('deprecated', '=', False)],
        default=lambda self: self._context.get('account_id', False))
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade", 
        help="The move of this entry line.", index=True, required=True)
    narration = fields.Text(related='move_id.narration', string='Internal Note')
    ref = fields.Char(related='move_id.ref', string='Reference', store=True)
    statement_id = fields.Many2one('account.bank.statement', string='Statement', 
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconcile_id = fields.Many2one('account.move.reconcile', string='Reconcile', 
        readonly=True, ondelete='set null', index=True, copy=False)
    reconcile_partial_id = fields.Many2one('account.move.reconcile', string='Partial Reconcile',
        readonly=True, ondelete='set null', index=True, copy=False)
    reconcile_ref = fields.Char(compute='_get_reconcile', string='Reconcile Ref', oldname='reconcile', store=True)
    amount_currency = fields.Float(string='Amount Currency', default=0.0,  digits=dp.get_precision('Account'),
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    amount_residual_currency = fields.Float(compute='_amount_residual', string='Residual Amount in Currency',
        help="The residual amount on a receivable or payable of a journal entry expressed "\
        "in its currency (maybe different of the company currency).")
    amount_residual = fields.Float(compute='_amount_residual', string='Residual Amount',
        help="The residual amount on a receivable or payable of a journal entry expressed in the company currency.")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self._get_currency(), 
        help="The optional other currency if it is a multi-currency entry.")
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal',
        default=lambda self: self._get_journal, required=True, index=True, store=True)
    period_id = fields.Many2one('account.period', related='move_id.period_id', string='Period',
        default=lambda self: self._get_period, required=True, index=True, store=True)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, ondelete='restrict')
    date_maturity = fields.Date(string='Due date', index=True ,
        help="This field is used for payable and receivable journal entries. "\
        "You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Effective date', required=True,
        index=True, default=lambda self: self._get_date, store=True)
    date_created = fields.Date(string='Creation date', index=True, default=fields.Date.context_today)
    analytic_lines = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')
    centralisation = fields.Selection([('normal','Normal'),('credit','Credit Centralisation'), ('debit','Debit Centralisation'),
        ('currency','Currency Adjustment')], default='normal', string='Centralisation', size=8)
    balance = fields.Float(compute='_balance', search=_balance_search, string='Balance')
    state = fields.Selection([('draft','Unbalanced'), ('valid','Balanced')], 
        string='Status', default='draft', readonly=True, copy=False)
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Account', 
        help="The Account can either be a base tax code or a tax code account.")
    tax_amount = fields.Float(string='Tax/Base Amount', digits=dp.get_precision('Account'), index=True, 
        help="If the Tax account is a tax code account, this field will contain the taxed amount."\
        "If the tax account is base tax code, this field will contain the basic amount(without tax).")
    account_tax_id =fields.Many2one('account.tax', string='Tax', copy=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', related='account_id.company_id',
        string='Company', store=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move.line'))
    invoice = fields.Many2one('account.invoice', string='Invoice')

    @api.model
    def _get_date(self):
        date = time.strftime('%Y-%m-%d')
        context = dict(self._context or {})
        if context.get('journal_id') and context.get('period_id'):
            line = self.search([('journal_id', '=', context['journal_id']),('period_id', '=', context['period_id'])], order='id desc', limit=1)
            if line:
                date = line.date
            else:
                period = self.env['account.period'].browse(context['period_id'])
                date = period.date_start
        return date

    @api.model
    def _get_currency(self):
        currency = False
        context = dict(self._context or {})
        if context.get('journal_id', False):
            currency = self.env['account.journal'].browse(context['journal_id']).currency
        return currency

    @api.model
    def _get_period(self):
        """
        Return  default account period value
        """
        context = dict(self._context or {})
        if context.get('period_id', False):
            return context['period_id']
        periods = self.env['account.period'].find()
        return periods and periods[0] or False

    @api.model
    def _get_journal(self):
        """
        Return journal based on the journal type
        """
        context = dict(self._context or {})
        if context.get('journal_id', False):
            return context['journal_id']
        journal = False

        if context.get('journal_type', False):
            journal = self.env['account.journal'].search([('type','=', context.get('journal_type'))], limit=1)
            if not journal:
                action_id = self.env.ref('account.action_account_journal_form')
                msg = _("""Cannot find any account journal of "%s" type for this company, You should create one.\n Please go to Journal Configuration""") % context.get('journal_type').replace('_', ' ').title()
                raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        return journal

    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    def _auto_init(self, cr, context=None):
        res = super(account_move_line, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'account_move_line_journal_id_period_id_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_journal_id_period_id_index ON account_move_line (journal_id, period_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_move_line_date_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_date_id_index ON account_move_line (date DESC, id desc)')
        return res

    @api.multi
    @api.constrains('account_id')
    def _check_no_view(self):
        for line in self:
            if line.account_id.type in ('view', 'consolidation'):
                raise Warning(_('You cannot create journal items on an account of type view or consolidation.'))

    @api.multi
    @api.constrains('account_id')
    def _check_no_closed(self):
        for line in self:
            if line.account_id.type == 'closed':
                raise Warning(_('You cannot create journal items on a closed account %s %s.') % (line.account_id.code, line.account_id.name))

    @api.multi
    @api.constrains('company_id')
    def _check_company_id(self):
        for line in self:
            if line.company_id != line.account_id.company_id or line.company_id != line.period_id.company_id:
                raise Warning(_('Account and Period must belong to the same company.'))

    @api.multi
    @api.constrains('date')
    def _check_date(self):
        for line in self:
            if line.journal_id.allow_date:
                if not time.strptime(line.date[:10],'%Y-%m-%d') >= time.strptime(line.period_id.date_start, '%Y-%m-%d') or not time.strptime(line.date[:10], '%Y-%m-%d') <= time.strptime(line.period_id.date_stop, '%Y-%m-%d'):
                    raise Warning(_('The date of your Journal Entry is not in the defined period! You should change the date or remove this constraint from the journal.'))

    @api.multi
    @api.constrains('currency_id')
    def _check_currency(self):
        for line in self:
            if line.account_id.currency_id:
                if not line.currency_id or not line.currency_id.id == line.account_id.currency_id.id:
                    raise Warning(_('The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account or select a multi-currency view on the journal.'))

    @api.multi
    @api.constrains('currency_id','amount_currency')
    def _check_currency_and_amount(self):
        for line in self:
            if (line.amount_currency and not line.currency_id):
                raise Warning(_("You cannot create journal items with a secondary currency without recording both 'currency' and 'amount currency' field."))

    @api.multi
    @api.constrains('amount_currency')
    def _check_currency_amount(self):
        for line in self:
            if line.amount_currency:
                if (line.amount_currency > 0.0 and line.credit > 0.0) or (line.amount_currency < 0.0 and line.debit > 0.0):
                    raise Warning(_('The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.'))

    @api.multi
    @api.constrains('currency_id')
    def _check_currency_company(self):
        for line in self:
            if line.currency_id.id == line.company_id.currency_id.id:
                raise Warning(_('You cannot provide a secondary currency if it is the same than the company one.'))

    #TODO: ONCHANGE_ACCOUNT_ID: set account_tax_id
    #Not used in account module itself. Need to check in other modules.
    @api.multi
    def onchange_currency(self, account_id, amount, currency_id, date=False, journal=False):
        if (not currency_id) or (not account_id):
            return {}
        result = {}
        acc = self.env['account.account'].browse(account_id)
        if (amount > 0) and journal:
            x = self.env['account.journal'].browse(journal).default_credit_account_id
            if x: acc = x
        context = dict(self._context)
        context.update({
                'date': date,
                'res.currency.compute.account': acc,
            })
        v = self.env['res.currency'].compute(currency_id, acc.company_id.currency_id.id, amount)
        result['value'] = {
            'debit': v > 0 and v or 0.0,
            'credit': v < 0 and -v or 0.0
        }
        return result

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.date_maturity = False

        if self.partner_id:
            date = self.date or datetime.now().strftime('%Y-%m-%d')
            journal_type = self.journal_id.type
    
            payment_term_id = False
            if journal_type in ('purchase', 'purchase_refund') and self.partner_id.property_supplier_payment_term:
                payment_term_id = self.partner_id.property_supplier_payment_term.id
            elif self.partner_id.property_payment_term:
                payment_term_id = self.partner_id.property_payment_term.id
            if payment_term_id:
                res = self.env['account.payment.term'].compute(payment_term_id, 100, date)
                if res:
                    self.date_maturity = res[0][0]
            if not self.account_id:
                account_payable = self.partner_id.property_account_payable.id
                account_receivable =  self.partner_id.property_account_receivable.id
                if journal_type in ('sale', 'purchase_refund'):
                    self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_receivable)
                elif journal_type in ('purchase', 'sale_refund'):
                    self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_payable)
                elif journal_type in ('general', 'bank', 'cash'):
                    if self.partner_id.customer:
                        self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_receivable)
                    elif self.partner_id.supplier:
                        self.account_id = self.partner_id and self.partner_id.property_account_position.map_account(account_payable)
                if self.account_id:
                    self.onchange_account_id()

    @api.onchange('account_id')
    def onchange_account_id(self):
        if self.account_id:
            if self.account_id.tax_ids and self.partner_id:
                self.account_tax_id = self.env['account.fiscal.position'].map_tax(self.partner_id and self.partner_id.property_account_position or False, self.account_id.tax_ids)[0]
            else:
                self.account_tax_id = self.account_id.tax_ids and self.account_id.tax_ids[0].id or False
    #
    # type: the type if reconciliation (no logic behind this field, for info)
    #
    # writeoff; entry generated for the difference between the lines
    #
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context
        if context.get('fiscalyear'):
            args.append(('period_id.fiscalyear_id', '=', context.get('fiscalyear', False)))
        if context.get('next_partner_only', False):
            if not context.get('partner_id', False):
                partner = self.list_partners_to_reconcile()
                if partner:
                    partner = partner[0]
            else:
                partner = context.get('partner_id', False)
            if not partner:
                return []
            args.append(('partner_id', '=', partner[0]))
        return super(account_move_line, self).search(args, offset, limit, order, count=count)

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param target_currency: curreny you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        if not self:
            return []
        company_currency = self.env.user.company_id.currency_id
        rml_parser = report_sxw.rml_parse(self._cr, self._uid, 'reconciliation_widget_aml', self._context)
        reconcile_partial_ids = []  # for a partial reconciliation, take only one line
        ret = []

        for line in self:
            if line.reconcile_partial_id and line.reconcile_partial_id.id in reconcile_partial_ids:
                continue
            if line.reconcile_partial_id:
                reconcile_partial_ids.append(line.reconcile_partial_id.id)

            ret_line = {
                'id': line.id,
                'name': line.move_id.name,
                'ref': line.move_id.ref,
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'period_name': line.period_id.name,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
            }

            # Get right debit / credit:
            line_currency = line.currency_id or company_currency
            amount_currency_str = ""
            if line.currency_id and line.amount_currency:
                amount_currency_str = rml_parser.formatLang(line.amount_currency, currency_obj=line.currency_id)
            if target_currency and line_currency == target_currency and target_currency != company_currency:
                debit = line.debit > 0 and line.amount_residual_currency or 0.0
                credit = line.credit > 0 and line.amount_residual_currency or 0.0
                amount_currency_str = rml_parser.formatLang(line.amount_residual, currency_obj=company_currency)
                amount_str = rml_parser.formatLang(debit or credit, currency_obj=target_currency)
            else:
                debit = line.debit > 0 and line.amount_residual or 0.0
                credit = line.credit > 0 and line.amount_residual or 0.0
                amount_str = rml_parser.formatLang(debit or credit, currency_obj=company_currency)
                if target_currency and target_currency != company_currency:
                    amount_currency_str = rml_parser.formatLang(debit or credit, currency_obj=line_currency)
                    ctx = context.copy()
                    if target_date:
                        ctx.update({'date': target_date})
                    debit = target_currency.with_context(ctx).compute(company_currency.id, debit)
                    credit = target_currency.with_context(ctx).compute(company_currency.id, credit)
                    amount_str = rml_parser.formatLang(debit or credit, currency_obj=target_currency)

            ret_line['credit'] = credit
            ret_line['debit'] = debit
            ret_line['amount_str'] = amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret.append(ret_line)
        return ret

    @api.model
    def list_partners_to_reconcile(self):
        self._cr.execute(
             """SELECT partner_id FROM (
                SELECT l.partner_id, p.last_reconciliation_date, SUM(l.debit) AS debit, SUM(l.credit) AS credit, MAX(l.create_date) AS max_date
                FROM account_move_line l
                RIGHT JOIN account_account a ON (a.id = l.account_id)
                RIGHT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE a.reconcile IS TRUE
                    AND l.reconcile_id IS NULL
                    AND l.state != 'draft'
                    GROUP BY l.partner_id, p.last_reconciliation_date
                ) AS s
                WHERE debit > 0 AND credit > 0 AND (last_reconciliation_date IS NULL OR max_date > last_reconciliation_date)
                ORDER BY last_reconciliation_date""")
        ids = [x[0] for x in self._cr.fetchall()]
        if not ids:
            return []

        # To apply the ir_rules
        partners = self.env['res.partner'].search([('id', 'in', ids)])
        return partners.name_get()

    @api.multi
    def reconcile_partial(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        move_rec_obj = self.env['account.move.reconcile']
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        company_list = []
        for line in self:
            if company_list and not line.company_id.id in company_list:
                raise Warning(_('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)

        for line in self:
            if line.account_id.currency_id:
                currency_id = line.account_id.currency_id
            else:
                currency_id = line.company_id.currency_id
            if line.reconcile_id:
                raise Warning(_("Journal Item '%s' (id: %s), Move '%s' is already reconciled!") % (line.name, line.id, line.move_id.name))
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if line2.state != 'valid':
                        raise Warning(_("Journal Item '%s' (id: %s) cannot be used in a reconciliation as it is not balanced!") % (line2.name, line2.id))
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2)
                        if line2.account_id.currency_id:
                            total += line2.amount_currency
                        else:
                            total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id)
            else:
                unmerge.append(line)
                if line.account_id.currency_id:
                    total += line.amount_currency
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if currency_id.is_zero(total):
            for line in merges+unmerge:
                res = line.reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
            return res
        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(self._context, novalidate=True)
        r_id = move_rec_obj.with_context(reconcile_context).create({
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), [line.id for line in merges+unmerge])
        })
        recs = [r_id] + merges_rec
        recs.with_context(reconcile_context).reconcile_partial_check()
        return r_id

    @api.multi
    def reconcile(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        unrec_lines = filter(lambda x: not x['reconcile_id'], self)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        context = self._context
        company_list = []
        ids = self.ids
        for line in self:
            if company_list and not line.company_id.id in company_list:
                raise Warning(_('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)
        for line in unrec_lines:
            if line.state != 'valid':
                raise Warning(_('Entry "%s" is not valid !') % line.name)
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit

        # Ifdate_p in context => take this date
        if context.has_key('date_p') and context['date_p']:
            date=context['date_p']
        else:
            date = time.strftime('%Y-%m-%d')

        self._cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(self.ids), ))
        r = self._cr.fetchall()
        #TODO: move this check to a constraint in the account_move_reconcile object
        if len(r) != 1:
            raise Warning(_('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise Warning(_('Entry is already reconciled.'))
        account = self.env['account.account'].browse(account_id)
        if not account.reconcile:
            raise Warning(_('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise Warning(_('Some entries are already reconciled.'))

        if (not account.company_id.currency_id.is_zero(writeoff)) or \
           (account.currency_id and (not account.currency_id.is_zero(currency))):
            if not writeoff_acc_id:
                raise Warning(_('You have to provide an account for the write off/exchange difference entry.'))
            if writeoff > 0:
                debit = writeoff
                credit = 0.0
                self_credit = writeoff
                self_debit = 0.0
            else:
                debit = 0.0
                credit = -writeoff
                self_credit = 0.0
                self_debit = -writeoff
            # If comment exist in context, take it
            if 'comment' in context and context['comment']:
                libelle = context['comment']
            else:
                libelle = _('Write-Off')

            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = line.account_id.company_id.currency_id.with_context({'date': line.date}).compute(context.get('currency_id',False), abs(line.debit-line.credit))
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name': libelle,
                    'debit': self_debit,
                    'credit': self_credit,
                    'account_id': account_id,
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name': libelle,
                    'debit': debit,
                    'credit': credit,
                    'account_id': writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]

            
            writeoff_move_id = self.env['account.move'].create({
                'period_id': writeoff_period_id,
                'journal_id': writeoff_journal_id,
                'company_id': writeoff_journal_id and self.env['account.journal'].browse(writeoff_journal_id).company_id.id or False,
                'date': date,
                'state': 'draft',
                'line_id': writeoff_lines
            })

            writeoff_line_ids = self.search([('move_id', '=', writeoff_move_id.id), ('account_id', '=', account_id)]).ids
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(context, novalidate=True)
        r_id = self.env['account.move.reconcile'].with_context(reconcile_context).create({
            'type': type,
            'line_id': map(lambda x: (4, x, False), self.ids),
            'line_partial_ids': map(lambda x: (3, x, False), self.ids)
        })
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            workflow.trg_trigger(self._uid, 'account.move.line', id, self._cr)

        #To FIX: Here 'self.partner_id' doesn't work and it gives Expected singleton error.
        partner = self[0].partner_id
        if partner and not partner.has_something_to_reconcile():
            partner.mark_as_reconciled()
        return r_id

    @api.one
    def view_header_get(self, view_type):
        context = self._context
#         context = self.convert_to_period(cr, user, context=context)
        if context.get('account_id', False):
            self._cr.execute('SELECT code FROM account_account WHERE id = %s', (context['account_id'], ))
            res = self._cr.fetchone()
            if res:
                res = _('Entries: ')+ (res[0] or '')
            return res
        if (not context.get('journal_id', False)) or (not context.get('period_id', False)):
            return False
        if context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        self._cr.execute('SELECT code FROM account_journal WHERE id = %s', (context['journal_id'], ))
        j = self._cr.fetchone()[0] or ''
        self._cr.execute('SELECT code FROM account_period WHERE id = %s', (context['period_id'], ))
        p = self._cr.fetchone()[0] or ''
        if j or p:
            return j + (p and (':' + p) or '')
        return False

    @api.onchange('date')
    def onchange_date(self):
        """
        Returns a dict that contains new values and context
        @param date: latest value from user input for field date
        """
        res = {}
        pids = self.env['account.period'].find(self.date)
        if pids:
            res['period_id'] = pids[0]
            context = dict(self._context or {}, period_id = pids[0])
        return {
            'value':res,
            'context':context,
        }

    @api.model
    def _check_moves(self):
        # use the first move ever created for this journal and period
        self._cr.execute('SELECT id, state, name FROM account_move WHERE journal_id = %s AND period_id = %s ORDER BY id limit 1', (self._context['journal_id'],self._context['period_id']))
        res = self._cr.fetchone()
        if res:
            if res[1] != 'draft':
                raise Warning(_('The account move (%s) for centralisation ' \
                                'has been confirmed.') % res[2])
        return res

    @api.multi
    def _remove_move_reconcile(self, opening_reconciliation=False):
        # Function remove move rencocile ids related with moves
        obj_move_rec = self.env['account.move.reconcile']
        unlink_ids = []
        if not self:
            return True
        full_recs = filter(lambda x: x.reconcile_id, self)
        rec_ids = [rec['reconcile_id'][0] for rec in full_recs]
        part_recs = filter(lambda x: x.reconcile_partial_id, self)
        part_rec_ids = [rec['reconcile_partial_id'][0] for rec in part_recs]
        unlink_ids += rec_ids
        unlink_ids += part_rec_ids
        all_moves = self.search(['|',('reconcile_id', 'in', unlink_ids),('reconcile_partial_id', 'in', unlink_ids)])
        all_moves = list(set(all_moves) - set(self))
        if unlink_ids:
            if opening_reconciliation:
                raise Warning(_('Opening Entries have already been generated.  Please run "Cancel Closing Entries" wizard to cancel those entries and then run this wizard.'))
                obj_move_rec.write(unlink_ids, {'opening_reconciliation': False})
            obj_move_rec.unlink(unlink_ids)
            if len(all_moves) >= 2:
                all_moves.reconcile_partial()
        return True

    @api.multi
    def unlink(self, check=True):
        self._update_check()
        result = False
        moves = set()
        context = dict(self._context or {})
        for line in self:
            moves.add(line.move_id)
            context['journal_id'] = line.journal_id.id
            context['period_id'] = line.period_id.id
            result = super(account_move_line, line).with_context(context).unlink()
        moves = list(moves)
        if check and moves:
            moves.with_context(context).validate()
        return result

    @api.multi
    def write(self, vals, check=True, update_check=True):
        if vals.get('account_tax_id', False):
            raise Warning(_('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and not self.env['account.account'].read(vals['account_id'], ['deprecated'])['deprecated']:
            raise Warning(_('You cannot use deprecated account.'))
        if update_check:
            if ('account_id' in vals) or ('journal_id' in vals) or ('period_id' in vals) or ('move_id' in vals) or ('debit' in vals) or ('credit' in vals) or ('date' in vals):
                self._update_check()

        todo_date = None
        if vals.get('date', False):
            todo_date = vals['date']
            del vals['date']

        for line in self:
            ctx = dict(self._context or {})
            if not ctx.get('journal_id'):
                if line.move_id:
                   ctx['journal_id'] = line.move_id.journal_id.id
                else:
                    ctx['journal_id'] = line.journal_id.id
            if not ctx.get('period_id'):
                if line.move_id:
                    ctx['period_id'] = line.move_id.period_id.id
                else:
                    ctx['period_id'] = line.period_id.id
            #Check for centralisation
            journal = self.env['account.journal'].with_context(ctx).browse(ctx['journal_id'])
            if journal.centralisation:
                self.with_context(ctx)._check_moves()
        result = super(account_move_line, self).write(vals)
        if check:
            done = []
            for line in self:
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    line.move_id.validate()
                    if todo_date:
                        line.move_id.write({'date': todo_date})
        return result

    @api.model
    def _update_journal_check(self, journal_id, period_id):
        #account_journal_period have been removed
#         self._cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
#         result = self._cr.fetchall()
#         journal = self.env['account.journal'].browse(journal_id)
#         period = self.env['account.period'].browse(period_id)
#         for (state,) in result:
#             if state == 'done':
#                 raise osv.except_osv(_('Error!'), _('You can not add/modify entries in a closed period %s of journal %s.' % (period.name,journal.name)))
#         if not result:
#             self.env['account.journal.period'].create({
#                 'name': (journal.code or journal.name)+':'+(period.name or ''),
#                 'journal_id': journal.id,
#                 'period_id': period.id
#             })
        return True

    @api.multi
    def _update_check(self):
        done = {}
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft' and (not line.journal_id.entry_posted):
                raise Warning(_('You cannot do this modification on a confirmed entry. You can just change some non legal fields or you must unconfirm the journal entry first.\n%s.') % err_msg)
            if line.reconcile_id:
                raise Warning(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            t = (line.journal_id.id, line.period_id.id)
            if t not in done:
                self._update_journal_check(line.journal_id.id, line.period_id.id)
                done[t] = True
        return True

    @api.model
    def create(self, vals, check=True):
        AccountObj = self.env['account.account']
        TaxObj = self.env['account.tax']
        MoveObj = self.env['account.move']
        context = dict(self._context or {})
        if vals.get('move_id', False):
            move = MoveObj.browse(vals['move_id'])
            if move.company_id:
                vals['company_id'] = move.company_id.id
            if move.date and not vals.get('date'):
                vals['date'] = move.date
        if ('account_id' in vals) and AccountObj.browse(vals['account_id']).deprecated:
            raise Warning(_('You cannot use deprecated account.'))
        if 'journal_id' in vals and vals['journal_id']:
            context['journal_id'] = vals['journal_id']
        if 'period_id' in vals and vals['period_id']:
            context['period_id'] = vals['period_id']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = MoveObj.browse(vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['period_id'] = m.period_id.id
        #we need to treat the case where a value is given in the context for period_id as a string
        if 'period_id' in context and not isinstance(context.get('period_id', ''), (int, long)):
            period_candidate_ids = self.env['account.period'].name_search(name=context.get('period_id',''))
            if len(period_candidate_ids) != 1:
                raise Warning(_('No period found or more than one period found for the given date.'))
            context['period_id'] = period_candidate_ids[0][0]
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        self.with_context(context)._update_journal_check(context['journal_id'], context['period_id'])
        move_id = vals.get('move_id', False)
        journal = self.env['account.journal'].browse(context['journal_id'])
        vals['journal_id'] = vals.get('journal_id') or context.get('journal_id')
        vals['period_id'] = vals.get('period_id') or context.get('period_id')
        vals['date'] = vals.get('date') or context.get('date')
        if not move_id:
            if journal.centralisation:
                #Check for centralisation
                res = self._check_moves()
                if res:
                    vals['move_id'] = res[0]
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').next_by_id(cr, uid, journal.sequence_id.id)
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'period_id': context['period_id'],
                        'journal_id': context['journal_id']
                    }
                    if vals.get('ref', ''):
                        v.update({'ref': vals['ref']})
                    move_id = MoveObj.with_context(context).create(v)
                    vals['move_id'] = move_id.id
                else:
                    raise Warning(_('Cannot create an automatic sequence for this piece.\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
        ok = not (journal.type_control_ids or journal.account_control_ids)
        if ('account_id' in vals):
            account = AccountObj.browse(vals['account_id'])
            if journal.type_control_ids:
                type = account.user_type
                for t in journal.type_control_ids:
                    if type.code == t.code:
                        ok = True
                        break
            if journal.account_control_ids and not ok:
                for a in journal.account_control_ids:
                    if a.id == vals['account_id']:
                        ok = True
                        break
            # Automatically convert in the account's secondary currency if there is one and
            # the provided values were not already multi-currency
            if account.currency_id and 'amount_currency' not in vals and account.currency_id.id != account.company_id.currency_id.id:
                vals['currency_id'] = account.currency_id.id
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                vals['amount_currency'] = account.company_id.currency_id.with_context(ctx).compute(
                    account.currency_id.id, vals.get('debit', 0.0) - vals.get('credit', 0.0))
        if not ok:
            raise Warning(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

        result = super(account_move_line, self).create(vals)
        # CREATE Taxes
        if vals.get('account_tax_id', False):
            tax_id = TaxObj.browse(vals['account_tax_id'])
            total = vals['debit'] - vals['credit']
            base_code = 'base_code_id'
            tax_code = 'tax_code_id'
            account_id = 'account_collected_id'
            base_sign = 'base_sign'
            tax_sign = 'tax_sign'
            if journal.type in ('purchase_refund', 'sale_refund') or (journal.type in ('cash', 'bank') and total < 0):
                base_code = 'ref_base_code_id'
                tax_code = 'ref_tax_code_id'
                account_id = 'account_paid_id'
                base_sign = 'ref_base_sign'
                tax_sign = 'ref_tax_sign'
            tmp_cnt = 0
            for tax in TaxObj.compute_all([tax_id], total, 1.00, force_excluded=False).get('taxes'):
                #create the base movement
                if tmp_cnt == 0:
                    if tax[base_code]:
                        tmp_cnt += 1
                        if tax_id.price_include:
                            total = tax['price_unit']
                        newvals = {
                            'tax_code_id': tax[base_code],
                            'tax_amount': tax[base_sign] * abs(total),
                        }
                        if tax_id.price_include:
                            if tax['price_unit'] < 0:
                                newvals['credit'] = abs(tax['price_unit'])
                            else:
                                newvals['debit'] = tax['price_unit']
                        result.with_context(context).write(newvals)
                else:
                    data = {
                        'move_id': vals['move_id'],
                        'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                        'date': vals['date'],
                        'partner_id': vals.get('partner_id', False),
                        'ref': vals.get('ref', False),
                        'statement_id': vals.get('statement_id', False),
                        'account_tax_id': False,
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                        'account_id': vals['account_id'],
                        'credit': 0.0,
                        'debit': 0.0,
                    }
                    if data['tax_code_id']:
                        self.with_context(context).create(data)
                #create the Tax movement
                data = {
                    'move_id': vals['move_id'],
                    'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id',False),
                    'ref': vals.get('ref',False),
                    'statement_id': vals.get('statement_id', False),
                    'account_tax_id': False,
                    'tax_code_id': tax[tax_code],
                    'tax_amount': tax[tax_sign] * abs(tax['amount']),
                    'account_id': tax[account_id] or vals['account_id'],
                    'credit': tax['amount']<0 and -tax['amount'] or 0.0,
                    'debit': tax['amount']>0 and tax['amount'] or 0.0,
                }
                if data['tax_code_id']:
                    self.with_context(context).create(data)
            del vals['account_tax_id']

        if check and not context.get('novalidate') and (context.get('recompute', True) or journal.entry_posted):
            move = MoveObj.browse(vals['move_id'])
            tmp = move.with_context(context).validate()
            if journal.entry_posted and tmp:
                move.with_context(context).button_validate()
        return result

    @api.model
    def list_periods(self):
        periods = self.env['account.period'].search([])
        return periods.name_get()

    @api.model
    def list_journals(self):
        ng = dict(self.env['account.journal'].name_search('',[]))
        ids = ng.keys()
        result = []
        for journal in self.env['account.journal'].browse(ids):
            result.append((journal.id, ng[journal.id], journal.type, bool(journal.currency), bool(journal.analytic_journal_id)))
        return result
