# -*- coding: utf-8 -*-

from operator import itemgetter
import time
from openerp.exceptions import UserError

from openerp import api, fields, models, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.misc import formatLang


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _description = 'Fiscal Position'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(string='Fiscal Position', required=True)
    active = fields.Boolean(default=True,
        help="By unchecking the active field, you may hide a fiscal position without deleting it.")
    company_id = fields.Many2one('res.company', string='Company')
    account_ids = fields.One2many('account.fiscal.position.account', 'position_id', string='Account Mapping', copy=True)
    tax_ids = fields.One2many('account.fiscal.position.tax', 'position_id', string='Tax Mapping', copy=True)
    note = fields.Text('Notes')
    auto_apply = fields.Boolean(string='Automatic', help="Apply automatically this fiscal position.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    country_id = fields.Many2one('res.country', string='Countries',
        help="Apply only if delivery or invoicing country match.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery or invocing country match the group.")

    @api.one
    @api.constrains('country_id', 'country_group_id')
    def _check_country(self):
        if self.country_id and self.country_group_id:
            raise UserError(_('You can not select a country and a group of countries.'))

    @api.v7
    def map_tax(self, cr, uid, fposition_id, taxes, context=None):
        if not taxes:
            return []
        if not fposition_id:
            return map(lambda x: x.id, taxes)
        result = set()
        for t in taxes:
            ok = False
            for tax in fposition_id.tax_ids:
                if tax.tax_src_id.id == t.id:
                    if tax.tax_dest_id:
                        result.add(tax.tax_dest_id.id)
                    ok = True
            if not ok:
                result.add(t.id)
        return list(result)

    @api.v8     # noqa
    def map_tax(self, taxes):
        result = self.env['account.tax'].browse()
        for tax in taxes:
            tax_count = 0
            for t in self.tax_ids:
                if t.tax_src_id == tax:
                    tax_count += 1
                    if t.tax_dest_id:
                        result |= t.tax_dest_id
            if not tax_count:
                result |= tax
        return result

    @api.v7
    def map_account(self, cr, uid, fposition_id, account_id, context=None):
        if not fposition_id:
            return account_id
        for pos in fposition_id.account_ids:
            if pos.account_src_id.id == account_id:
                account_id = pos.account_dest_id.id
                break
        return account_id

    @api.v8
    def map_account(self, account):
        for pos in self.account_ids:
            if pos.account_src_id == account:
                return pos.account_dest_id
        return account

    @api.v8
    def map_accounts(self, accounts):
        """ Receive a dictionary having accounts in values and try to replace those accounts accordingly to the fiscal position.
        """
        ref_dict = {}
        for line in self.account_ids:
            ref_dict[line.account_src_id] = line.account_dest_id
        for key, acc in accounts.items():
            if acc in ref_dict:
                accounts[key] = ref_dict[acc]
        return accounts

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        if not partner_id:
            return False
        # This can be easily overriden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)

        # partner manually set fiscal position always win
        if partner.property_account_position:
            return partner.property_account_position.id

        # if no delivery use invocing
        if delivery_id:
            delivery = PartnerObj.browse(delivery_id)
        else:
            delivery = partner

        domains = [[('auto_apply', '=', True), ('vat_required', '=', partner.vat_subjected)]]
        if partner.vat_subjected:
            # Possibly allow fallback to non-VAT positions, if no VAT-required position matches
            domains += [[('auto_apply', '=', True), ('vat_required', '=', False)]]

        for domain in domains:
            if delivery.country_id.id:
                fiscal_position = self.search(domain + [('country_id', '=', delivery.country_id.id)], limit=1)
                if fiscal_position:
                    return fiscal_position.id

                fiscal_position = self.search(domain + [('country_group_id.country_ids', '=', delivery.country_id.id)], limit=1)
                if fiscal_position:
                    return fiscal_position.id

            fiscal_position = self.search(domain + [('country_id', '=', None), ('country_group_id', '=', None)], limit=1)
            if fiscal_position:
                return fiscal_position.id
        return False


class AccountFiscalPositionTax(models.Model):
    _name = 'account.fiscal.position.tax'
    _description = 'Taxes Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax', string='Tax Source', required=True)
    tax_dest_id = fields.Many2one('account.tax', string='Replacement Tax')

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id,tax_dest_id)',
         'A tax fiscal position could be defined only once time on same taxes.')
    ]


class AccountFiscalPositionAccount(models.Model):
    _name = 'account.fiscal.position.account'
    _description = 'Accounts Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    account_src_id = fields.Many2one('account.account', string='Account Source',
        domain=[('deprecated', '=', False)], required=True)
    account_dest_id = fields.Many2one('account.account', string='Account Destination',
        domain=[('deprecated', '=', False)], required=True)

    _sql_constraints = [
        ('account_src_dest_uniq',
         'unique (position_id,account_src_id,account_dest_id)',
         'An account fiscal position could be defined only once time on same accounts.')
    ]


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Partner'

    @api.multi
    def _credit_debit_get(self):
        where_clause, where_params = self.env['account.move.line']._query_get()
        where_params = [tuple(self.ids)] + where_params
        self._cr.execute("""SELECT l.partner_id, act.type, SUM(l.debit-l.credit)
                      FROM account_move_line l
                      LEFT JOIN account_account a ON (l.account_id=a.id)
                      LEFT JOIN account_account_type act ON (a.user_type=act.id)
                      WHERE act.type IN ('receivable','payable')
                      AND l.partner_id IN %s
                      AND l.reconciled IS FALSE
                      """ + where_clause + """
                      GROUP BY l.partner_id, act.type
                      """, where_params)
        for pid, type, val in self._cr.fetchall():
            partner = self.browse(pid)
            if type == 'receivable':
                partner.credit = val
            elif type == 'payable':
                partner.debit = -val

    @api.multi
    def _asset_difference_search(self, type, args):
        if not args:
            return []
        having_values = tuple(map(itemgetter(2), args))
        where = ' AND '.join(
            map(lambda x: '(SUM(bal2) %(operator)s %%s)' % {
                                'operator':x[1]},args))
        query = self.env['account.move.line']._query_get()
        self._cr.execute(('SELECT pid AS partner_id, SUM(bal2) FROM ' \
                    '(SELECT CASE WHEN bal IS NOT NULL THEN bal ' \
                    'ELSE 0.0 END AS bal2, p.id as pid FROM ' \
                    '(SELECT (debit-credit) AS bal, partner_id ' \
                    'FROM account_move_line l ' \
                    'WHERE account_id IN ' \
                            '(SELECT id FROM account_account '\
                            'WHERE type=%s AND active) ' \
                    'AND reconciled IS FALSE ' \
                    'AND '+query+') AS l ' \
                    'RIGHT JOIN res_partner p ' \
                    'ON p.id = partner_id ) AS pl ' \
                    'GROUP BY pid HAVING ' + where),
                    (type,) + having_values)
        res = self._cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', map(itemgetter(0), res))]

    @api.multi
    def _credit_search(self, args):
        return self._asset_difference_search('receivable', args)

    @api.multi
    def _debit_search(self, args):
        return self._asset_difference_search('payable', args)

    @api.multi
    def _invoice_total(self):
        account_invoice_report = self.env['account.invoice.report']
        if not self.ids:
            self.total_invoiced = 0.0
            return True
        for partner in self:
            invoices = account_invoice_report.search([('partner_id', 'child_of', partner.id), ('state', 'not in', ['draft', 'cancel'])])
            partner.total_invoiced = sum(inv.user_currency_price_total for inv in invoices)

    @api.multi
    def _journal_item_count(self):
        for partner in self:
            partner.journal_item_count = self.env['account.move.line'].search_count([('partner_id', '=', partner.id)])
            partner.contracts_count = self.env['account.analytic.account'].search_count([('partner_id', '=', partner.id)])

    def get_followup_lines_domain(self, date, overdue_only=False, only_unblocked=False):
        domain = [('reconciled', '=', False), ('account_id.deprecated', '=', False), ('account_id.internal_type', '=', 'receivable')]
        if only_unblocked:
            domain += [('blocked', '=', False)]
        if self.ids:
            domain += [('partner_id', 'in', self.ids)]
        #adding the overdue lines
        overdue_domain = ['|', '&', ('date_maturity', '!=', False), ('date_maturity', '<=', date), '&', ('date_maturity', '=', False), ('date', '<=', date)]
        if overdue_only:
            domain += overdue_domain
        return domain

    @api.multi
    def _compute_issued_total(self):
        """ Returns the issued total as will be displayed on partner view """
        today = fields.Date.context_today(self)
        for partner in self:
            domain = partner.get_followup_lines_domain(today, overdue_only=True)
            issued_total = 0
            for aml in self.env['account.move.line'].search(domain):
                issued_total += aml.amount_residual
            partner.issued_total = formatLang(self.env, issued_total, currency_obj=self.env.user.company_id.currency_id)

    @api.one
    def _compute_has_unreconciled_entries(self):
        # Avoid useless work if has_unreconciled_entries is not relevant for this partner
        if not self.active or not self.is_company and self.parent_id:
            return
        self.env.cr.execute(
            """ SELECT 1 FROM(
                    SELECT
                        p.last_time_entries_checked AS last_time_entries_checked,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        RIGHT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE
                        p.id = %s
                        AND EXISTS (
                            SELECT 1
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            AND l.partner_id = p.id
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT 1
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            AND l.partner_id = p.id
                            AND l.amount_residual < 0
                        )
                    GROUP BY p.last_time_entries_checked
                ) as s
                WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
            """ % (self.id,))
        self.has_unreconciled_entries = self.env.cr.rowcount == 1

    @api.multi
    def mark_as_reconciled(self):
        return self.write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    @api.one
    def _get_company_currency(self):
        if self.company_id:
            self.currency_id = self.company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    vat_subjected = fields.Boolean('VAT Legal Statement',
        help="Check this box if the partner is subjected to the VAT. It will be used for the VAT legal statement.")
    credit = fields.Monetary(compute='_credit_debit_get', search=_credit_search,
        string='Total Receivable', help="Total amount this customer owes you.")
    debit = fields.Monetary(compute='_credit_debit_get', search=_debit_search, string='Total Payable',
        help="Total amount you have to pay to this supplier.")
    debit_limit = fields.Monetary('Payable Limit')
    total_invoiced = fields.Monetary(compute='_invoice_total', string="Total Invoiced",
        groups='account.group_account_invoice')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', store=True, readonly=True,
        help='Utility field to express amount currency')

    contracts_count = fields.Integer(compute='_journal_item_count', string="Contracts", type='integer')
    journal_item_count = fields.Integer(compute='_journal_item_count', string="Journal Items", type="integer")
    issued_total = fields.Char(compute='_compute_issued_total', string="Journal Items")
    property_account_payable = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True)
    property_account_receivable = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=True)
    property_account_position = fields.Many2one('account.fiscal.position', company_dependent=True,
        string="Fiscal Position",
        help="The fiscal position will determine taxes and accounts used for the partner.")
    property_payment_term = fields.Many2one('account.payment.term', company_dependent=True,
        string ='Customer Payment Term',
        help="This payment term will be used instead of the default one for sale orders and customer invoices")
    property_supplier_payment_term = fields.Many2one('account.payment.term', company_dependent=True,
         string ='Supplier Payment Term',
         help="This payment term will be used instead of the default one for purchase orders and supplier bills")
    ref_companies = fields.One2many('res.company', 'partner_id',
        string='Companies that refers to partner')
    has_unreconciled_entries = fields.Boolean(compute='_compute_has_unreconciled_entries',
        help="The partner has at least one unreconciled debit and credit since last time the invoices & payments matching was performed.")
    last_time_entries_checked = fields.Datetime(oldname='last_reconciliation_date',
        string='Latest Invoices & Payments Matching Date', readonly=True, copy=False,
        help='Last time the invoices & payments matching was performed for this partner. '
             'It is set either if there\'s not at least an unreconciled debit and an unreconciled credit '
             'or if you click the "Done" button.')
    invoice_ids = fields.One2many('account.invoice', 'partner_id', string='Invoices', readonly=True, copy=False)
    contract_ids = fields.One2many('account.analytic.account', 'partner_id', string='Contracts', readonly=True)

    def _find_accounting_partner(self, partner):
        ''' Find the partner for which the accounting entries will be created '''
        return partner.commercial_partner_id

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['debit_limit', 'property_account_payable', 'property_account_receivable', 'property_account_position',
             'property_payment_term', 'property_supplier_payment_term', 'last_time_entries_checked']
