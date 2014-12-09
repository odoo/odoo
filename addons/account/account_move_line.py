# -*- coding: utf-8 -*-

import time
from datetime import datetime

from openerp import workflow
from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.exceptions import RedirectWarning, Warning
import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.report import report_sxw
from openerp.tools import float_is_zero


class account_partial_reconcile(models.Model):
    _name = "account.partial.reconcile"
    _table = "account_partial_reconcile_rel"
    _description = "Partial Reconcile"

    source_move_id = fields.Many2one('account.move.line')
    rec_move_id = fields.Many2one('account.move.line')
    amount = fields.Float()
    amount_currency = fields.Float()

class account_move_line(models.Model):
    _name = "account.move.line"
    _description = "Journal Items"
    _order = "date desc, id desc"

    @api.model
    def _query_get(self, obj='l'):
        fiscalyear_obj = self.env['account.fiscalyear']
        account_obj = self.env['account.account']
        fiscalyear_ids = []
        context = dict(self._context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
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
        if initial_bal and not context.get('periods', False) and not where_move_lines_by_date:
            #we didn't pass any filter in the context, and the initial balance can't be computed using only the fiscalyear otherwise entries will be summed twice
            #so we have to invalidate this query
            raise Warning(_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))


        if context.get('journal_ids', False):
            query += ' AND '+obj+'.journal_id IN (%s)' % ','.join(map(str, context['journal_ids']))

        if context.get('chart_account_id', False):
            child_ids = account_obj.browse(context['chart_account_id'])._get_children_and_consol()
            if child_ids:
                query += ' AND '+obj+'.account_id IN (%s)' % ','.join(map(str, child_ids))

        query += company_clause
        return query

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
                vals_line = self._prepare_analytic_line(obj_line)
                self.env['account.analytic.line'].create(vals_line)

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
    @api.depends('reconcile_id','reconcile_partial_id')
    def _get_reconcile(self):
        for line in self:
            if line.reconcile_id:
                line.reconcile_ref = line.reconcile_id.name
            elif line.reconcile_partial_id:
                if line.reconcile_partial_id.name == '/':
                    line.reconcile_ref = line.reconcile_partial_id.move_id.ref
                else:
                    line.reconcile_ref = line.reconcile_partial_id.name
            # To get rid of Error: Field account.move.line.reconcile_ref is accessed before being computed.
            else:
                line.reconcile_ref = False

    # @api.depends('reconcile_partial_ids.debit', 'reconcile_partial_ids.credit')
    # def _is_reconciled(self):
    #     for line in self:
    #         total = self.debit if self.debit != 0.0 else self.credit
    #         for partial_reconcile_line in self.env['account_partial_reconcile'].search([('source_move_id', '=', line.id), ('rec_move_id', '=', line.id)]):
    #         # for partial_reconcile_line in self.reconcile_partial_ids:
    #             total += partial_reconcile_line.amount
    #         if float_zero(total, dp.get_precision('Account')):
    #             line.reconciled = True
    #         else:
    #             line.reconciled = False

    @api.depends('debit', 'credit', 'amount_currency', 'currency_id', 
        'reconcile_partial_ids.debit', 'reconcile_partial_ids.credit', 
        'account_id.reconcile')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconciliable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconciliable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines. """
        for line in self:

            if line.reconciled:
                line.amount_residual = 0.0
                line.amount_residual_currency = 0.0
                continue

            amount = line.debit - line.credit

            for rec_line in self.env['account.partial.reconcile'].search([('source_move_id', '=', line.id), ('rec_move_id', '=', line.id)]):
                    amount += rec_line.amount

            line.amount_residual = amount
            if line.currency_id:
                line.amount_residual_currency = line.company_id.currency_id.compute(amount, line.currency_id)
                digits_rounding_precision = line.currency_id.rounding
            else:
                line.amount_residual_currency = 0.0
                digits_rounding_precision = line.company_id.currency_id.rounding

            if float_zero(amount, digits_rounding_precision):
                line.reconciled = True
            else:
                line.reconciled = False

            # if line.reconcile_id or not line.account_id.reconcile:
            #     line.amount_residual = 0.0
            #     line.amount_residual_currency = 0.0
            #     continue
            
            # amount = line.currency_id and line.amount_currency or line.debit - line.credit

            # for rec_line in line.reconcile_partial_with_ids:
            #     if rec_line.currency_id and line.currency_id and rec_line.currency_id.id == line.currency_id.id:
            #         amount += rec_line.amount_currency
            #     elif not rec_line.currency_id and not line.currency_id:
            #         amount += (rec_line.debit - rec_line.credit)
            #     else:
            #         payment_line_amount = rec_line.currency_id and rec_line.amount_currency or rec_line.debit - rec_line.credit
            #         from_currency = rec_line.currency_id or rec_line.company_id.currency_id
            #         from_currency = rec_line.with_context(date=rec_line.date)
            #         to_currency = line.currency_id or line.company_id.currency_id
            #         amount += from_currency.compute(payment_line_amount, to_currency)

            # if line.reconcile_partial_id:
            #     payment_line = line.reconcile_partial_id
            #     if payment_line.currency_id and line.currency_id and payment_line.currency_id.id == line.currency_id.id:
            #         amount += payment_line.amount_currency if abs(payment_line.amount_currency)<=abs(amount) else -amount
            #     elif not payment_line.currency_id and not line.currency_id:
            #         amount += (payment_line.debit - payment_line.credit) if abs((payment_line.debit - payment_line.credit))<=abs(amount) else -amount
            #     else:
            #         payment_line_amount = payment_line.currency_id and payment_line.amount_currency or payment_line.debit - payment_line.credit
            #         from_currency = payment_line.currency_id or payment_line.company_id.currency_id
            #         from_currency = from_currency.with_context(date=payment_line.date)
            #         to_currency = line.currency_id or line.company_id.currency_id
            #         convert_amount = from_currency.compute(payment_line_amount, to_currency)
            #         amount += convert_amount if abs(convert_amount)<=abs(amount) else -amount

            # if line.currency_id:
            #     line.amount_residual = line.currency_id.compute(amount, line.company_id.currency_id)
            #     line.amount_residual_currency = amount
            # else:
            #     line.amount_residual = amount
            #     line.amount_residual_currency = 0.0

    @api.model
    def _get_currency(self):
        currency = False
        context = dict(self._context or {})
        if context.get('default_journal_id', False):
            currency = self.env['account.journal'].browse(context['default_journal_id']).currency
        return currency

    @api.model
    def _get_journal(self):
        """ Return journal based on the journal type """
        context = dict(self._context or {})
        journal_id = context.get('journal_id', False)
        if journal_id:
            return journal_id

        journal_type = context.get('journal_type', False)
        if journal_type:
            recs = self.env['account.journal'].search([('type','=',journal_type)])
            if not recs:
                action = self.env.ref('account.action_account_journal_form')
                msg = _("""Cannot find any account journal of "%s" type for this company, You should create one.\n Please go to Journal Configuration""") % journal_type.replace('_', ' ').title()
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            journal_id = recs[0].id
        return journal_id

    name = fields.Char(string='Name', required=True)
    quantity = fields.Float(string='Quantity', digits=(16,2), 
        help="The optional quantity expressed by this line, eg: number of product sold. "\
        "The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Float(string='Debit', digits=dp.get_precision('Account'), default=0.0)
    credit = fields.Float(string='Credit', digits=dp.get_precision('Account'), default=0.0)
    amount_currency = fields.Float(string='Amount Currency', default=0.0,  digits=dp.get_precision('Account'),
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Currency', default=_get_currency, 
        help="The optional other currency if it is a multi-currency entry.")
    amount_residual = fields.Float(compute='_amount_residual', string='Residual Amount', store=True, digits=dp.get_precision('Account'),
        help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Float(compute='_amount_residual', string='Residual Amount in Currency', store=True, digits=dp.get_precision('Account'),
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
        ondelete="cascade", domain=[('deprecated', '=', False)],
        default=lambda self: self._context.get('account_id', False))
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade", 
        help="The move of this entry line.", index=True, required=True)
    narration = fields.Text(related='move_id.narration', string='Internal Note')
    ref = fields.Char(related='move_id.ref', string='Reference', store=True)
    statement_id = fields.Many2one('account.bank.statement', string='Statement', 
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconciled = fields.Boolean(compute='_amount_residual', store=True)
    reconcile_id = fields.Many2one('account.move.reconcile', string='Reconcile', 
        readonly=True, ondelete='set null', index=True, copy=False) #TO BE REMOVED
    reconcile_partial_ids = fields.Many2many('account.move.line', 'account_partial_reconcile_rel', 'source_move_id', 'rec_move_id', string='Partial Reconcile')
    reconcile_partial_id = fields.Many2one('account.move.line', string='Partial Reconcile',
        readonly=True, ondelete='set null', index=True, copy=False) #TO BE REMOVED
    reconcile_partial_with_ids = fields.One2many('account.move.line', 'reconcile_partial_id', 
        String="Reconciled with", help="Show the lines implied in partial reconciliation for this move line") #TO BE REMOVED
    reconcile_ref = fields.Char(compute='_get_reconcile', string='Reconcile Ref', oldname='reconcile', store=True) #TO BEREMOVED
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal',
        default=_get_journal, required=True, index=True, store=True)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")

    date_maturity = fields.Date(string='Due date', index=True ,
        help="This field is used for payable and receivable journal entries. "\
        "You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Effective date', required=True,
        index=True, default=fields.Date.context_today, store=True)
    analytic_lines = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')

    # TODO: remove with the new tax engine
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Account', 
        help="The Account can either be a base tax code or a tax code account.")
    tax_amount = fields.Float(string='Tax/Base Amount', digits=dp.get_precision('Account'), index=True, 
        help="If the Tax account is a tax code account, this field will contain the taxed amount."\
        "If the tax account is base tax code, this field will contain the basic amount(without tax).")

    account_tax_id = fields.Many2many('account.tax', string='Tax', copy=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', related='account_id.company_id',
        string='Company', store=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move.line'))

    # TODO: put the invoice link and partner_id on the account_move
    invoice = fields.Many2one('account.invoice', string='Invoice')
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, ondelete='restrict')

    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    @api.multi
    @api.constrains('account_id')
    def _check_account_type(self):
        for line in self:
            if line.account_id.user_type.type == 'consolidation':
                raise Warning(_('You cannot create journal items on an account of type consolidation.'))

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
                self.account_tax_id = self.env['account.fiscal.position'].map_tax(self.partner_id and self.partner_id.property_account_position or False, self.account_id.tax_ids)
            else:
                self.account_tax_id = self.account_id.tax_ids or False

    @api.v7
    def get_data_for_manual_reconciliation(self, cr, uid, res_type, res_id=None, context=None):
        """ Returns the data required for the  manual reconciliation of a given partner/account.
            If no id is passed, returns data for all partners/accounts that can be reconciled.
            :param res_type: either 'partner' or 'account' """

        is_partner = res_type == 'partner'
        res_id_condition = res_id and 'AND r.id = '+str(res_id) or ''
        cr.execute(
            """ SELECT * FROM (
                    SELECT %s
                        -- to_char(a.last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked,
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.create_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        %s
                    WHERE
                        a.reconcile IS TRUE
                        -- AND l.state <> 'draft'
                        -- TODO : improve those 2 subqueries ?
                        %s
                        %s
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            -- AND l.state <> 'draft'
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            -- AND l.state <> 'draft'
                            AND l.amount_residual > 0
                        )
                    GROUP BY %s a.id, a.name, a.code --, a.last_time_entries_checked
                    -- ORDER BY last_time_entries_checked
                ) as s
                WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
            """ % (
                is_partner and "p.id AS partner_id, to_char(p.last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked, p.name AS partner_name,"
                    or "to_char(a.last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked,",
                is_partner and "RIGHT JOIN res_partner p ON (l.partner_id = p.id)" or "",
                not is_partner and "AND a.type <> 'payable' AND a.type <> 'receivable'" or "",
                res_id_condition,
                is_partner and "l.partner_id, p.id," or "",
            ))

        # Apply ir_rules by filtering out
        rows = cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(self.env['account.account'].browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(self.pool.get('res.partner').browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Fetch other data
        for row in rows:
            account = self.env['account.account'].browse(row['account_id'])
            row['currency_id'] = account.currency_id.id or account.company_currency_id.id
            partner_id = is_partner and row['partner_id'] or False
            row['reconciliation_proposition'] = account.get_reconciliation_proposition(partner_id=partner_id)

        return rows

    @api.v7
    def get_reconciliation_proposition(self, cr, uid, account_id, partner_id=False, context=None):
        return self.browse(account_id).get_reconciliation_proposition(partner_id)

    @api.one
    def get_reconciliation_proposition(self, partner_id=False):
        """ Returns two lines whose amount are opposite """
        partner_id_condition = partner_id and 'AND a.partner_id = %d AND b.partner_id = %d' % (partner_id, partner_id) or ''
        account_id = self.id

        # Get pairs
        # TODO : once amount_residual is stored, use it and remove 'reconcile_partial_id IS NULL'
        cr.execute(
            """ SELECT a.id, b.id
                FROM account_move_line a, account_move_line b
                WHERE ((a.debit = b.credit AND a.debit <> 0) OR
                      (a.currency_id = b.currency_id AND a.amount_currency = - b.amount_currency AND a.amount_currency <> 0))
                AND a.reconcile_partial_id IS NULL AND b.reconcile_partial_id IS NULL
                AND a.state = 'valid' AND b.state = 'valid' AND a.reconcile_id IS NULL AND b.reconcile_id IS NULL
                AND a.account_id = %d AND b.account_id = %d
                %s
                ORDER BY a.date asc
                LIMIT 10
            """ % (account_id, account_id, partner_id_condition))
        pairs = cr.fetchall()

        # Apply ir_rules by filtering out
        all_pair_ids = [element for tupl in pairs for element in tupl]
        allowed_ids = set(self.env['account.move.line'].browse(all_pair_ids).ids)
        pairs = [pair for pair in pairs if pair[0] in allowed_ids and pair[1] in allowed_ids]

        # Return lines formatted
        if len(pairs) > 0:
            target_currency = self.currency_id or self.company_currency_id
            lines = self.browse(list(pairs[0]))
            return lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)
        else:
            return []

    @api.v7
    def get_move_lines_for_manual_reconciliation(self, cr, uid, account_id, partner_id=False, excluded_ids=None, str=False, offset=0, limit=None, target_currency_id=False, context=None):
        """ Returns unreconciled move lines for an account or a partner+account, formatted for the manual reconciliation widget """
        # Complete domain
        additional_domain = [('reconcile_id', '=', False), ('account_id','=',account_id)]
        if partner_id:
            additional_domain.append(('partner_id','=',partner_id))

        # Fetch lines
        lines = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str, offset=offset, limit=limit, additional_domain=additional_domain)
        if target_currency_id:
            target_currency = self.env['res.currency'].browse(target_currency_id)
        else:
            account = self.env['account.account'].browse(account_id)
            target_currency = account.currency_id or account.company_currency_id
        return lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)

    @api.model
    def _domain_move_lines_for_reconciliation(self, excluded_ids=None, str=False, additional_domain=None):
        context = (self._context or {})
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        else:
            additional_domain = expression.normalize_domain(additional_domain)

        additional_domain = expression.AND([additional_domain, [('state', '=', 'valid')]])
        if excluded_ids:
            additional_domain = expression.AND([additional_domain, [('id', 'not in', excluded_ids)]])
        if str:
            str_domain = [
                '|', ('move_id.name', 'ilike', str),
                '|', ('move_id.ref', 'ilike', str),
                '|', ('date_maturity', 'like', str),
                '&', ('name', '!=', '/'), ('name', 'ilike', str)
            ]
            # Warning : this is undue coupling. But building this domain is really tricky.
            # What follows means : "If building a domain for the bank statement reconciliation, id there's no partner
            # and a search string, we want to find the string in any of those fields including the partner name
            if 'bank_statement_line' in context and not context['bank_statement_line'].partner_id.id:
                str_domain = expression.OR([str_domain, [('partner_id.name', 'ilike', str)]])

            additional_domain = expression.AND([additional_domain, str_domain])
            # TODO : store fields amount_residual and amount_residual_currency when migrating to new API
            # try:
            #     amount = float(str)
            #     additional_domain += ['|', ('amount_residual', '=', amount), '|', ('amount_residual_currency', '=', amount), '|', ('amount_residual', '=', -amount), ('amount_residual_currency', '=', -amount)]
            # except:
            #     pass

        return additional_domain

    @api.model
    def get_move_lines_for_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None):
        """ Find the move lines that could be used in a reconciliation. If count is true, only returns the number of lines.
            This function is used for bank statement reconciliation and manual reconciliation ; each use case's domain logic is expressed through additional_domain.

            :param st_line: the browse record of the statement line
            :param integers list excluded_ids: ids of move lines that should not be fetched
            :param boolean count: just return the number of records
            :param tuples list additional_domain: additional domain restrictions
        """
        domain = self._domain_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str, additional_domain=additional_domain)

        # Get move lines ; in case of a partial reconciliation, only consider one line
        filtered_lines = []
        reconcile_partial_ids = []
        actual_offset = offset
        while True:
            line_ids = self.search(domain, offset=actual_offset, limit=limit, order="date_maturity asc, id asc")
            lines = self.browse(line_ids)
            make_one_more_loop = False
            for line in lines:
                if line.id in reconcile_partial_ids:
                    #if we filtered a line because it is partially reconciled with an already selected line, we must do one more loop
                    #in order to get the right number of items in the pager
                    make_one_more_loop = True
                    continue
                filtered_lines.append(line)
                if line.reconcile_partial_ids:
                    reconcile_partial_ids.append(line.reconcile_partial_ids.ids)

            if not limit or not make_one_more_loop or len(filtered_lines) >= limit:
                break
            actual_offset = actual_offset + limit
        lines = limit and filtered_lines[:limit] or filtered_lines


        # Return count or lines
        if count:
            return len(lines)
        else:
            return lines

    @api.v7
    def prepare_move_lines_for_reconciliation_widget_by_ids(self, cr, uid, line_ids, target_currency_id=False, context=None):
        """ Bridge for reconciliation widget """
        target_currency = target_currency_id and self.env['res.currency'].browse(target_currency_id) or False
        return self.browse(line_ids).prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param target_currency: curreny you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
            :param skip_partial_reconciliation_siblings: do not construct the list of partial_reconciliation_siblings
        """
        context = dict(self._context or {})
        company_currency = self.env['res.users'].browse(uid).company_id.currency_id
        rml_parser = report_sxw.rml_parse(cr, uid, 'reconciliation_widget_aml', context=context)
        ret = []

        for line in self:
            partial_reconciliation_siblings = []
            if line.reconcile_partial_ids and not skip_partial_reconciliation_siblings:
                siblings = line.reconcile_partial_ids.copy() - line
                partial_reconciliation_siblings = prs_rs.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=target_date, skip_partial_reconciliation_siblings=True)

            ret_line = {
                'id': line.id,
                'name': line.name if line.name != '/' else line.move_id.name,
                'ref': line.move_id.ref,
                # for reconciliation with existing entries (eg. cheques)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'is_reconciled': not line.account_id.reconcile,
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'period_name': line.period_id.name,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'is_partially_reconciled': bool(line.reconcile_partial_ids),
                'partial_reconciliation_siblings': partial_reconciliation_siblings,
                'currency_id': line.currency_id.id or False,
            }

            # Amount residual can technically be negative (eg: you register a payment of 150€ on an invoice of 100€)
            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency
            if line.amount_residual < 0:
                debit, credit = credit, debit
                amount = -amount
                amount_currency = -amount_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if not line.account_id.reconcile:
                amount = abs(debit - credit)
                amount_currency = line.amount_currency

            # Get right debit / credit:
            target_currency = target_currency or company_currency
            line_currency = line.currency_id or company_currency
            amount_currency_str = ""
            total_amount_currency_str = ""
            if line_currency != company_currency:
                total_amount = line.amount_currency
                actual_debit = debit > 0 and amount_currency or 0.0
                actual_credit = credit > 0 and amount_currency or 0.0
            else:
                total_amount = abs(debit - credit)
                actual_debit = debit > 0 and amount or 0.0
                actual_credit = credit > 0 and amount or 0.0
            if line_currency != target_currency:
                amount_currency_str = rml_parser.formatLang(actual_debit or actual_credit, currency_obj=line_currency)
                total_amount_currency_str = rml_parser.formatLang(total_amount, currency_obj=line_currency)
                ret_line['credit_currency'] = actual_credit
                ret_line['debit_currency'] = actual_debit
                ctx = context.copy()
                if target_date:
                    ctx.update({'date': target_date})
                total_amount = line_currency.with_context(ctx).compute(total_amount, target_currency)
                actual_debit = line_currency.with_context(ctx).compute(actual_debit, target_currency)
                actual_credit = line_currency.with_context(ctx).compute(actual_credit, target_currency)
            amount_str = rml_parser.formatLang(actual_debit or actual_credit, currency_obj=target_currency)
            total_amount_str = rml_parser.formatLang(total_amount, currency_obj=target_currency)

            ret_line['debit'] = actual_debit
            ret_line['credit'] = actual_credit
            ret_line['amount_str'] = amount_str
            ret_line['total_amount_str'] = total_amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret_line['total_amount_currency_str'] = total_amount_currency_str
            ret.append(ret_line)
        return ret

    @api.v7
    def process_reconciliations(self, cr, uid, data, context=None):
        """ Used to validate a batch of reconciliations in a single call """
        for datum in data:
            id = datum['id']
            type = datum['type']
            mv_line_ids = datum['mv_line_ids']
            new_mv_line_dicts = datum['new_mv_line_dicts']

            if len(mv_line_ids) >= 1 or len(mv_line_ids) + len(new_mv_line_dicts) >= 2:
                self.process_reconciliation(cr, uid, mv_line_ids, new_mv_line_dicts, context=context)
        
            if type == 'partner':
                self.env['res.partner'].browse(id).mark_as_reconciled()
            if type == 'account':
                self.env['account.account'].browse(id).mark_as_reconciled()

    @api.v7
    def process_reconciliation(self, cr, uid, mv_line_ids, new_mv_line_dicts, context=None):
        """ Create new move lines from new_mv_line_dicts (if not empty) then call reconcile_partial on mv_line_ids and new move lines """

        if len(mv_line_ids) < 1 or len(mv_line_ids) + len(new_mv_line_dicts) < 2:
            raise osv.except_osv(_('Error!'), _('A reconciliation must involve at least 2 move lines.'))
        mv_lines = self.browse(mv_line_ids)
        
        # Create writeoff move lines
        writeoff_lines = []
        if len(new_mv_line_dicts) > 0:
            am_obj = self.env['account.move']
            account = mv_lines[0].account_id
            partner_id = mv_lines[0].partner_id.id
            company_currency = account.company_id.currency_id
            account_currency = account.currency_id or company_currency

            for mv_line_dict in new_mv_line_dicts:
                if mv_line_dict.get('is_tax_line'):
                    continue
                writeoff_dicts = []

                # Data for both writeoff lines
                for field in ['debit', 'credit', 'amount_currency']:
                    if field not in mv_line_dict:
                        mv_line_dict[field] = 0.0
                if account_currency != company_currency:
                    mv_line_dict['amount_currency'] = mv_line_dict['debit'] - mv_line_dict['credit']
                    mv_line_dict['currency_id'] = account_currency
                    mv_line_dict['debit'] = account_currency.compute(mv_line_dict['debit'], company_currency)
                    mv_line_dict['credit'] = account_currency.compute(mv_line_dict['credit'], company_currency)
                
                # Writeoff line in specified writeoff account
                first_line_dict = mv_line_dict.copy()
                if 'analytic_account_id' in first_line_dict:
                    del first_line_dict['analytic_account_id']
                writeoff_dicts.append((0, 0, first_line_dict))

                # Writeoff line in account being reconciled
                second_line_dict = mv_line_dict.copy()
                second_line_dict['account_id'] = account.id
                second_line_dict['partner_id'] = partner_id
                second_line_dict['debit'] = mv_line_dict['credit']
                second_line_dict['credit'] = mv_line_dict['debit']
                if account_currency != company_currency:
                    second_line_dict['amount_currency'] = -mv_line_dict['amount_currency']
                writeoff_dicts.append((0, 0, second_line_dict))

                # Create the move
                # TODO : account_move_prepare is no longer
                move_vals = am_obj.account_move_prepare(cr, uid, mv_line_dict['journal_id'], context=context)
                move_vals['line_id'] = writeoff_dicts
                move = am_obj.create(move_vals)
                writeoff_lines += move.line_id.filtered(lambda r: r.account_id == account.id)

        (mv_lines|writeoff_lines).reconcile_partial()

    @api.model
    def list_partners_to_reconcile(self):
        self._cr.execute(
             """SELECT partner_id FROM (
                SELECT l.partner_id, p.last_time_entries_checked, SUM(l.debit) AS debit, SUM(l.credit) AS credit, MAX(l.create_date) AS max_date
                FROM account_move_line l
                RIGHT JOIN account_account a ON (a.id = l.account_id)
                RIGHT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE a.reconcile IS TRUE
                    AND l.reconcile_id IS NULL
                    GROUP BY l.partner_id, p.last_time_entries_checked
                ) AS s
                WHERE debit > 0 AND credit > 0 AND (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
                ORDER BY last_time_entries_checked""")
        ids = [x[0] for x in self._cr.fetchall()]
        if not ids:
            return []

        # To apply the ir_rules
        partners = self.env['res.partner'].search([('id', 'in', ids)])
        return partners.name_get()

    @api.multi
    def reconcile_partial(self, main_reconcile_line, writeoff_acc_id=False, writeoff_period_date=False, writeoff_journal_id=False):
        currency = self.env['res.currency']
        total = 0.0
        # total = main_reconcile_line.amount_residual
        # if main_reconcile_line.account_id.currency_id:
        #     total = main_reconcile_line.amount_residual_currency
        start_amount = total
        company_ids = set([l.company_id.id for l in self+main_reconcile_line])
        if len(company_ids) > 1:
            raise Warning(_('To reconcile the entries company should be the same for all entries.'))
        lines_debit = lines_credit = False
        for line in self:
            if line.reconciled:
                raise Warning(_("Journal Item '%s' (id: %s), Move '%s' is already reconciled!") % (line.name, line.id, line.move_id.name))
            # if line.reconcile_partial_id:
            #     raise Warning(_("Journal Item '%s' (id: %s), is already partially reconciled with \
            #         Journal Item '%s' (id: %s)!") % (line.name, line.id, line.reconcile_partial_id.name, line.reconcile_partial_id.id))
            if line.debit > 0:
                lines_debit = True
            else:
                lines_credit = True
            if line.account_id.currency_id:
                currency = line.account_id.currency_id
                total += line.amount_residual_currency
            else:
                currency = line.company_id.currency_id
                total += line.amount_residual
            res = self.env['account.partial.reconcile'].create({'source_move_id': main_reconcile_line.id, 'rec_move_id': line.id, 'amount': total,})
        if (lines_debit and lines_credit) or (main_reconcile_line.debit > 0 and lines_debit) or (main_reconcile_line.credit > 0 and lines_credit):
            raise Warning(_("You are trying to reconcile a line with wrong lines (payment with another payment, or invoice with anoter invoice)"))
        if (start_amount <= 0 and total > 0) or (start_amount >= 0 and total < 0):
            raise Warning(_("You are trying to reconcile an entry with too much lines or with a line having a larger quantity"))
        
        res = self.env['account.partial.reconcile'].create({'source_move_id': main_reconcile_line.id, 'rec_move_id': self.id, 'amount': total,})
        return res

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_period_date=False, writeoff_journal_id=False):
        unrec_lines = filter(lambda x: not x['reconcile_id'], self)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        context = self._context
        ids = self.ids
        company_ids = set([l.company_id.id for l in self])
        if len(company_ids) > 1:
            raise Warning(_('To reconcile the entries company should be the same for all entries.'))
        for line in unrec_lines:
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
            'line_id': map(lambda x: (4, x, False), self.ids),
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

    @api.multi
    def _remove_move_reconcile(self):
        # Function remove move rencocile ids related with moves
        if not self:
            return True
        full_recs = []
        partial_recs = []
        for account_move_line in self:
            if account_move_line.reconcile_id:
                full_recs.append(account_move_line.reconcile_id.id)
            if account_move_line.reconcile_partial_id:
                partial_recs.append(account_move_line.reconcile_partial_id.id)
        self.env['account.move.reconcile'].browse(full_recs).unlink()
        self.browse(partial_recs).write({'reconcile_partial_id': False})
        return True

    @api.multi
    def unlink(self, check=True):
        self._update_check()
        result = False
        moves = self.env['account.move']
        context = dict(self._context or {})
        for line in self:
            moves += line.move_id
            context['journal_id'] = line.journal_id.id
            context['date'] = line.date
            line.with_context(context)
            result = super(account_move_line, line).unlink()
        if check and moves:
            moves.with_context(context)._post_validate()
        return result

    @api.multi
    def write(self, vals, check=True, update_check=True):
        if vals.get('account_tax_id', False):
            raise Warning(_('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and not self.env['account.account'].read(vals['account_id'], ['deprecated'])['deprecated']:
            raise Warning(_('You cannot use deprecated account.'))
        if update_check:
            if ('account_id' in vals) or ('journal_id' in vals) or ('date' in vals) or ('move_id' in vals) or ('debit' in vals) or ('credit' in vals) or ('date' in vals):
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
            if not ctx.get('date'):
                if line.move_id:
                    ctx['date'] = line.move_id.date
                else:
                    ctx['date'] = line.date
        result = super(account_move_line, self).write(vals)
        if check:
            done = []
            for line in self:
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    line.move_id._post_validate()
                    if todo_date:
                        line.move_id.write({'date': todo_date})
        return result

    @api.model
    def _update_journal_check(self, journal_id, date):
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
            t = (line.journal_id.id, line.date)
            if t not in done:
                self._update_journal_check(line.journal_id.id, line.date)
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
        if 'date' in vals and vals['date']:
            context['date'] = vals['date']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = MoveObj.browse(vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['date'] = m.date
        #we need to treat the case where a value is given in the context for period_id as a string
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        if 'date' not in context:
            context['date'] = fields.Date.context_today(self)
        self.with_context(context)._update_journal_check(context['journal_id'], context['date'])
        move_id = vals.get('move_id', False)
        journal = self.env['account.journal'].browse(context['journal_id'])
        vals['journal_id'] = vals.get('journal_id') or context.get('journal_id')
        vals['date'] = vals.get('date') or context.get('date')
        vals['date'] = vals.get('date') or context.get('date')
        if not move_id:
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').next_by_id(cr, uid, journal.sequence_id.id)
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
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
        tax_ids = vals.get('account_tax_id') and vals.get('account_tax_id')[0][2] or []
        for taxid in tax_ids:
            tax_id = TaxObj.browse(taxid)
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
            # TODO: FIX ME
            # move.with_context(context)._post_validate()
            if journal.entry_posted:
                move.with_context(context).button_validate()
        return result

    @api.model
    def list_journals(self):
        ng = dict(self.env['account.journal'].name_search('',[]))
        ids = ng.keys()
        result = []
        for journal in self.env['account.journal'].browse(ids):
            result.append((journal.id, ng[journal.id], journal.type, bool(journal.currency), bool(journal.analytic_journal_id)))
        return result
