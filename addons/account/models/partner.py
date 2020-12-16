# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import logging

from psycopg2 import sql, DatabaseError

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP

_logger = logging.getLogger(__name__)

class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _description = 'Fiscal Position'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(string='Fiscal Position', required=True)
    active = fields.Boolean(default=True,
        help="By unchecking the active field, you may hide a fiscal position without deleting it.")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    account_ids = fields.One2many('account.fiscal.position.account', 'position_id', string='Account Mapping', copy=True)
    tax_ids = fields.One2many('account.fiscal.position.tax', 'position_id', string='Tax Mapping', copy=True)
    note = fields.Text('Notes', translate=True, help="Legal mentions that have to be printed on the invoices.")
    auto_apply = fields.Boolean(string='Detect Automatically', help="Apply automatically this fiscal position.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    country_id = fields.Many2one('res.country', string='Country',
        help="Apply only if delivery country matches.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery country matches the group.")
    state_ids = fields.Many2many('res.country.state', string='Federal States')
    zip_from = fields.Char(string='Zip Range From')
    zip_to = fields.Char(string='Zip Range To')
    # To be used in hiding the 'Federal States' field('attrs' in view side) when selected 'Country' has 0 states.
    states_count = fields.Integer(compute='_compute_states_count')

    def _compute_states_count(self):
        for position in self:
            position.states_count = len(position.country_id.state_ids)

    @api.constrains('zip_from', 'zip_to')
    def _check_zip(self):
        for position in self:
            if position.zip_from and position.zip_to and position.zip_from > position.zip_to:
                raise ValidationError(_('Invalid "Zip Range", please configure it properly.'))

    def map_tax(self, taxes, product=None, partner=None):
        if not self:
            return taxes
        result = self.env['account.tax']
        for tax in taxes:
            taxes_correspondance = self.tax_ids.filtered(lambda t: t.tax_src_id == tax)
            result |= taxes_correspondance.tax_dest_id if taxes_correspondance else tax
        return result

    def map_account(self, account):
        for pos in self.account_ids:
            if pos.account_src_id == account:
                return pos.account_dest_id
        return account

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

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.zip_from = self.zip_to = self.country_group_id = False
            self.state_ids = [(5,)]
            self.states_count = len(self.country_id.state_ids)

    @api.onchange('country_group_id')
    def _onchange_country_group_id(self):
        if self.country_group_id:
            self.zip_from = self.zip_to = self.country_id = False
            self.state_ids = [(5,)]

    @api.model
    def _convert_zip_values(self, zip_from='', zip_to=''):
        max_length = max(len(zip_from), len(zip_to))
        if zip_from.isdigit():
            zip_from = zip_from.rjust(max_length, '0')
        if zip_to.isdigit():
            zip_to = zip_to.rjust(max_length, '0')
        return zip_from, zip_to

    @api.model
    def create(self, vals):
        zip_from = vals.get('zip_from')
        zip_to = vals.get('zip_to')
        if zip_from and zip_to:
            vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from, zip_to)
        return super(AccountFiscalPosition, self).create(vals)

    def write(self, vals):
        zip_from = vals.get('zip_from')
        zip_to = vals.get('zip_to')
        if zip_from or zip_to:
            for rec in self:
                vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from or rec.zip_from, zip_to or rec.zip_to)
        return super(AccountFiscalPosition, self).write(vals)

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False, zipcode=False, vat_required=False):
        if not country_id:
            return False
        base_domain = [
            ('auto_apply', '=', True),
            ('vat_required', '=', vat_required),
            ('company_id', 'in', [self.env.company.id, False]),
        ]
        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [('zip_from', '=', False), ('zip_to', '=', False)]
        null_country_dom = [('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode:
            zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_group = base_domain + [('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(domain_country + state_domain + zip_domain, limit=1)
        # return records that fit the most the criteria, and fallback on less specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(domain_country + null_state_dom + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(domain_country + state_domain + null_zip_dom, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(domain_country + null_state_dom + null_zip_dom, limit=1)

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(domain_group + null_state_dom + null_zip_dom, limit=1)

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(base_domain + null_country_dom, limit=1)
        return fpos

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        """
        :return: fiscal position found (recordset)
        :rtype: :class:`account.fiscal.position`
        """
        if not partner_id:
            return self.env['account.fiscal.position']

        # This can be easily overridden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)

        # if no delivery use invoicing
        if delivery_id:
            delivery = PartnerObj.browse(delivery_id)
        else:
            delivery = partner

        # partner manually set fiscal position always win
        if delivery.property_account_position_id or partner.property_account_position_id:
            return delivery.property_account_position_id or partner.property_account_position_id

        # First search only matching VAT positions
        vat_required = bool(partner.vat)
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_required)

        # Then if VAT required found no match, try positions that do not require it
        if not fp and vat_required:
            fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False)

        return fp or self.env['account.fiscal.position']


class AccountFiscalPositionTax(models.Model):
    _name = 'account.fiscal.position.tax'
    _description = 'Tax Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='position_id.company_id', store=True)
    tax_src_id = fields.Many2one('account.tax', string='Tax on Product', required=True, check_company=True)
    tax_dest_id = fields.Many2one('account.tax', string='Tax to Apply', check_company=True)

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id,tax_dest_id)',
         'A tax fiscal position could be defined only one time on same taxes.')
    ]


class AccountFiscalPositionAccount(models.Model):
    _name = 'account.fiscal.position.account'
    _description = 'Accounts Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='position_id.company_id', store=True)
    account_src_id = fields.Many2one('account.account', string='Account on Product',
        check_company=True, required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    account_dest_id = fields.Many2one('account.account', string='Account to Use Instead',
        check_company=True, required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")

    _sql_constraints = [
        ('account_src_dest_uniq',
         'unique (position_id,account_src_id,account_dest_id)',
         'An account fiscal position could be defined only one time on same accounts.')
    ]


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.depends_context('company')
    def _credit_debit_get(self):
        tables, where_clause, where_params = self.env['account.move.line'].with_context(state='posted', company_id=self.env.company.id)._query_get()
        where_params = [tuple(self.ids)] + where_params
        if where_clause:
            where_clause = 'AND ' + where_clause
        self._cr.execute("""SELECT account_move_line.partner_id, act.type, SUM(account_move_line.amount_residual)
                      FROM """ + tables + """
                      LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
                      LEFT JOIN account_account_type act ON (a.user_type_id=act.id)
                      WHERE act.type IN ('receivable','payable')
                      AND account_move_line.partner_id IN %s
                      AND account_move_line.reconciled IS NOT TRUE
                      """ + where_clause + """
                      GROUP BY account_move_line.partner_id, act.type
                      """, where_params)
        treated = self.browse()
        for pid, type, val in self._cr.fetchall():
            partner = self.browse(pid)
            if type == 'receivable':
                partner.credit = val
                if partner not in treated:
                    partner.debit = False
                    treated |= partner
            elif type == 'payable':
                partner.debit = -val
                if partner not in treated:
                    partner.credit = False
                    treated |= partner
        remaining = (self - treated)
        remaining.debit = False
        remaining.credit = False

    def _asset_difference_search(self, account_type, operator, operand):
        if operator not in ('<', '=', '>', '>=', '<='):
            return []
        if type(operand) not in (float, int):
            return []
        sign = 1
        if account_type == 'payable':
            sign = -1
        res = self._cr.execute('''
            SELECT partner.id
            FROM res_partner partner
            LEFT JOIN account_move_line aml ON aml.partner_id = partner.id
            JOIN account_move move ON move.id = aml.move_id
            RIGHT JOIN account_account acc ON aml.account_id = acc.id
            WHERE acc.internal_type = %s
              AND NOT acc.deprecated AND acc.company_id = %s
              AND move.state = 'posted'
            GROUP BY partner.id
            HAVING %s * COALESCE(SUM(aml.amount_residual), 0) ''' + operator + ''' %s''', (account_type, self.env.user.company_id.id, sign, operand))
        res = self._cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [r[0] for r in res])]

    @api.model
    def _credit_search(self, operator, operand):
        return self._asset_difference_search('receivable', operator, operand)

    @api.model
    def _debit_search(self, operator, operand):
        return self._asset_difference_search('payable', operator, operand)

    def _invoice_total(self):
        self.total_invoiced = 0
        if not self.ids:
            return True

        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self.filtered('id'):
            # price_total is in the company currency
            all_partners_and_children[partner] = self.with_context(active_test=False).search([('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        domain = [
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel']),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
        ]
        price_totals = self.env['account.invoice.report'].read_group(domain, ['price_subtotal'], ['partner_id'])
        for partner, child_ids in all_partners_and_children.items():
            partner.total_invoiced = sum(price['price_subtotal'] for price in price_totals if price['partner_id'][0] in child_ids)

    def _compute_journal_item_count(self):
        AccountMoveLine = self.env['account.move.line']
        for partner in self:
            partner.journal_item_count = AccountMoveLine.search_count([('partner_id', '=', partner.id)])

    def _compute_has_unreconciled_entries(self):
        for partner in self:
            # Avoid useless work if has_unreconciled_entries is not relevant for this partner
            if not partner.active or not partner.is_company and partner.parent_id:
                partner.has_unreconciled_entries = False
                continue
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
                """, (partner.id,))
            partner.has_unreconciled_entries = self.env.cr.rowcount == 1

    def mark_as_reconciled(self):
        self.env['account.partial.reconcile'].check_access_rights('write')
        return self.sudo().write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                partner.currency_id = self.env.company.currency_id

    credit = fields.Monetary(compute='_credit_debit_get', search=_credit_search,
        string='Total Receivable', help="Total amount this customer owes you.")
    debit = fields.Monetary(compute='_credit_debit_get', search=_debit_search, string='Total Payable',
        help="Total amount you have to pay to this vendor.")
    debit_limit = fields.Monetary('Payable Limit')
    total_invoiced = fields.Monetary(compute='_invoice_total', string="Total Invoiced",
        groups='account.group_account_invoice,account.group_account_readonly')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency", help='Utility field to express amount currency')
    journal_item_count = fields.Integer(compute='_compute_journal_item_count', string="Journal Items")
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=True)
    property_account_position_id = fields.Many2one('account.fiscal.position', company_dependent=True,
        string="Fiscal Position",
        domain="[('company_id', '=', current_company_id)]",
        help="The fiscal position determines the taxes/accounts used for this contact.")
    property_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
        string='Customer Payment Terms',
        domain="[('company_id', 'in', [current_company_id, False])]",
        help="This payment term will be used instead of the default one for sales orders and customer invoices")
    property_supplier_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
        string='Vendor Payment Terms',
        domain="[('company_id', 'in', [current_company_id, False])]",
        help="This payment term will be used instead of the default one for purchase orders and vendor bills")
    ref_company_ids = fields.One2many('res.company', 'partner_id',
        string='Companies that refers to partner')
    has_unreconciled_entries = fields.Boolean(compute='_compute_has_unreconciled_entries',
        help="The partner has at least one unreconciled debit and credit since last time the invoices & payments matching was performed.")
    last_time_entries_checked = fields.Datetime(
        string='Latest Invoices & Payments Matching Date', readonly=True, copy=False,
        help='Last time the invoices & payments matching was performed for this partner. '
             'It is set either if there\'s not at least an unreconciled debit and an unreconciled credit '
             'or if you click the "Done" button.')
    invoice_ids = fields.One2many('account.move', 'partner_id', string='Invoices', readonly=True, copy=False)
    contract_ids = fields.One2many('account.analytic.account', 'partner_id', string='Partner Contracts', readonly=True)
    bank_account_count = fields.Integer(compute='_compute_bank_count', string="Bank")
    trust = fields.Selection([('good', 'Good Debtor'), ('normal', 'Normal Debtor'), ('bad', 'Bad Debtor')], string='Degree of trust you have in this debtor', default='normal', company_dependent=True)
    invoice_warn = fields.Selection(WARNING_MESSAGE, 'Invoice', help=WARNING_HELP, default="no-message")
    invoice_warn_msg = fields.Text('Message for Invoice')
    # Computed fields to order the partners as suppliers/customers according to the
    # amount of their generated incoming/outgoing account moves
    supplier_rank = fields.Integer(default=0)
    customer_rank = fields.Integer(default=0)

    def _get_name_search_order_by_fields(self):
        res = super()._get_name_search_order_by_fields()
        partner_search_mode = self.env.context.get('res_partner_search_mode')
        if not partner_search_mode in ('customer', 'supplier'):
            return res
        order_by_field = 'COALESCE(res_partner.%s, 0) DESC,'
        if partner_search_mode == 'customer':
            field = 'customer_rank'
        else:
            field = 'supplier_rank'

        order_by_field = order_by_field % field
        return '%s, %s' % (res, order_by_field % field) if res else order_by_field

    def _compute_bank_count(self):
        bank_data = self.env['res.partner.bank'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(bank['partner_id'][0], bank['partner_id_count']) for bank in bank_data])
        for partner in self:
            partner.bank_account_count = mapped_data.get(partner.id, 0)

    def _find_accounting_partner(self, partner):
        ''' Find the partner for which the accounting entries will be created '''
        return partner.commercial_partner_id

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['debit_limit', 'property_account_payable_id', 'property_account_receivable_id', 'property_account_position_id',
             'property_payment_term_id', 'property_supplier_payment_term_id', 'last_time_entries_checked']

    def action_view_partner_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('partner_id', 'child_of', self.id),
        ]
        action['context'] = {'default_move_type':'out_invoice', 'move_type':'out_invoice', 'journal_type': 'sale', 'search_default_unpaid': 1}
        return action

    def can_edit_vat(self):
        ''' Can't edit `vat` if there is (non draft) issued invoices. '''
        can_edit_vat = super(ResPartner, self).can_edit_vat()
        if not can_edit_vat:
            return can_edit_vat
        has_invoice = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('partner_id', 'child_of', self.commercial_partner_id.id),
            ('state', '=', 'posted')
        ], limit=1)
        return can_edit_vat and not (bool(has_invoice))

    @api.model_create_multi
    def create(self, vals_list):
        search_partner_mode = self.env.context.get('res_partner_search_mode')
        is_customer = search_partner_mode == 'customer'
        is_supplier = search_partner_mode == 'supplier'
        if search_partner_mode:
            for vals in vals_list:
                if is_customer and 'customer_rank' not in vals:
                    vals['customer_rank'] = 1
                elif is_supplier and 'supplier_rank' not in vals:
                    vals['supplier_rank'] = 1
        return super().create(vals_list)

    def _increase_rank(self, field, n=1):
        if self.ids and field in ['customer_rank', 'supplier_rank']:
            try:
                with self.env.cr.savepoint(flush=False):
                    query = sql.SQL("""
                        SELECT {field} FROM res_partner WHERE ID IN %(partner_ids)s FOR UPDATE NOWAIT;
                        UPDATE res_partner SET {field} = {field} + %(n)s
                        WHERE id IN %(partner_ids)s
                    """).format(field=sql.Identifier(field))
                    self.env.cr.execute(query, {'partner_ids': tuple(self.ids), 'n': n})
                    for partner in self:
                        self.env.cache.remove(partner, partner._fields[field])
            except DatabaseError as e:
                if e.pgcode == '55P03':
                    _logger.debug('Another transaction already locked partner rows. Cannot update partner ranks.')
                else:
                    raise e
