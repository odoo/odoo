# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict

import math
import re


TYPE_TAX_USE = [
    ('sale', 'Sales'),
    ('purchase', 'Purchases'),
    ('none', 'None'),
]


class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _description = 'Tax Group'
    _order = 'sequence asc'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    property_tax_payable_account_id = fields.Many2one(
        comodel_name='account.account',
        company_dependent=True,
        string='Tax Payable Account',
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the authorities.")
    property_tax_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        company_dependent=True,
        string='Tax Receivable Account',
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the company.")
    property_advance_tax_payment_account_id = fields.Many2one(
        comodel_name='account.account',
        company_dependent=True,
        string='Tax Advance Account',
        help="Downpayments posted on this account will be considered by the Tax Closing Entry.")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="The country for which this tax group is applicable.")
    country_code = fields.Char(related="country_id.code")
    preceding_subtotal = fields.Char(
        string="Preceding Subtotal",
        help="If set, this value will be used on documents as the label of a subtotal excluding this tax group before displaying it. " \
             "If not set, the tax group will be displayed after the 'Untaxed amount' subtotal.",
    )

    @api.model
    def _check_misconfigured_tax_groups(self, company, countries):
        """ Searches the tax groups used on the taxes from company in countries that don't have
        at least a tax payable account, a tax receivable account or an advance tax payment account.

        :return: A boolean telling whether or not there are misconfigured groups for any
                 of these countries, in this company
        """

        # This cannot be refactored to check for misconfigured groups instead
        # because of an ORM limitation with search on property fields:
        # searching on property = False also returns the properties using the default value,
        # even if it's non-empty.
        # (introduced here https://github.com/odoo/odoo/pull/6044)
        all_configured_groups_ids = self.with_company(company)._search([
            ('property_tax_payable_account_id', '!=', False),
            ('property_tax_receivable_account_id', '!=', False),
        ])

        return bool(self.env['account.tax'].search([
            ('company_id', '=', company.id),
            ('tax_group_id', 'not in', all_configured_groups_ids),
            ('country_id', 'in', countries.ids),
        ], limit=1))


class AccountTax(models.Model):
    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence,id'
    _check_company_auto = True
    _rec_names_search = ['name', 'description']

    @api.model
    def _default_tax_group(self):
        return self.env.ref('account.tax_group_taxes')

    name = fields.Char(string='Tax Name', required=True)
    name_searchable = fields.Char(store=False, search='_search_name',
          help="This dummy field lets us use another search method on the field 'name'."
               "This allows more freedom on how to search the 'name' compared to 'filter_domain'."
               "See '_search_name' and '_parse_name_search' for why this is not possible with 'filter_domain'.")
    type_tax_use = fields.Selection(TYPE_TAX_USE, string='Tax Type', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group. 'adjustment' is used to perform tax adjustment.")
    tax_scope = fields.Selection([('service', 'Services'), ('consu', 'Goods')], string="Tax Scope", help="Restrict the use of taxes to a type of product.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')],
        help="""
    - Group of Taxes: The tax is a set of sub taxes.
    - Fixed: The tax amount stays the same whatever the price.
    - Percentage of Price: The tax amount is a % of the price:
        e.g 100 * (1 + 10%) = 110 (not price included)
        e.g 110 / (1 + 10%) = 100 (price included)
    - Percentage of Price Tax Included: The tax amount is a division of the price:
        e.g 180 / (1 - 10%) = 200 (not price included)
        e.g 200 * (1 - 10%) = 180 (price included)
        """)
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    children_tax_ids = fields.Many2many('account.tax',
        'account_tax_filiation_rel', 'parent_tax', 'child_tax',
        check_company=True,
        string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 4), default=0.0)
    real_amount = fields.Float(string='Real amount to apply', compute='_compute_real_amount', store=True)
    description = fields.Char(string='Label on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Base of Subsequent Taxes', default=False,
        help="If set, taxes with a higher sequence than this one will be affected by it, provided they accept it.")
    is_base_affected = fields.Boolean(
        string="Base Affected by Previous Taxes",
        default=True,
        help="If set, taxes with a lower sequence might affect this one, provided they try to do it.")
    analytic = fields.Boolean(string="Include in Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    tax_group_id = fields.Many2one('account.tax.group', string="Tax Group", default=_default_tax_group, required=True,
                                   domain="[('country_id', 'in', (country_id, False))]")
    # Technical field to make the 'tax_exigibility' field invisible if the same named field is set to false in 'res.company' model
    hide_tax_exigibility = fields.Boolean(string='Hide Use Cash Basis Option', related='company_id.tax_exigibility', readonly=True)
    tax_exigibility = fields.Selection(
        [('on_invoice', 'Based on Invoice'),
         ('on_payment', 'Based on Payment'),
        ], string='Tax Exigibility', default='on_invoice',
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
        "Based on Payment: the tax is due as soon as the payment of the invoice is received.")
    cash_basis_transition_account_id = fields.Many2one(string="Cash Basis Transition Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        comodel_name='account.account',
        help="Account used to transition the tax amount for cash basis taxes. It will contain the tax amount as long as the original invoice has not been reconciled ; at reconciliation, this amount cancelled on this account and put on the regular tax account.")
    invoice_repartition_line_ids = fields.One2many(string="Distribution for Invoices", comodel_name="account.tax.repartition.line", inverse_name="invoice_tax_id", copy=True, help="Distribution when the tax is used on an invoice")
    refund_repartition_line_ids = fields.One2many(string="Distribution for Refund Invoices", comodel_name="account.tax.repartition.line", inverse_name="refund_tax_id", copy=True, help="Distribution when the tax is used on a refund")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', required=True, help="The country for which this tax is applicable.")
    country_code = fields.Char(related='country_id.code', readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use, tax_scope)', 'Tax names must be unique !'),
    ]

    @api.constrains('tax_group_id')
    def validate_tax_group_id(self):
        for record in self:
            if record.tax_group_id.country_id and record.tax_group_id.country_id != record.country_id:
                raise ValidationError(_("The tax group must have the same country_id as the tax using it."))

    @api.model
    def default_get(self, fields_list):
        # company_id is added so that we are sure to fetch a default value from it to use in repartition lines, below
        rslt = super(AccountTax, self).default_get(fields_list + ['company_id'])

        company_id = rslt.get('company_id')
        company = self.env['res.company'].browse(company_id)

        if 'country_id' in fields_list:
            rslt['country_id'] = company.account_fiscal_country_id.id

        if 'refund_repartition_line_ids' in fields_list:
            rslt['refund_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'tag_ids': [], 'company_id': company_id}),
                (0, 0, {'repartition_type': 'tax', 'tag_ids': [], 'company_id': company_id}),
            ]

        if 'invoice_repartition_line_ids' in fields_list:
            rslt['invoice_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'tag_ids': [], 'company_id': company_id}),
                (0, 0, {'repartition_type': 'tax', 'tag_ids': [], 'company_id': company_id}),
            ]

        return rslt

    @staticmethod
    def _parse_name_search(name):
        """
        Parse the name to search the taxes faster.
        Technical:  0EUM      => 0%E%U%M
                    21M       => 2%1%M%   where the % represents 0, 1 or multiple characters in a SQL 'LIKE' search.
                    21" M"    => 2%1% M%
                    21" M"co  => 2%1% M%c%o%
        Examples:   0EUM      => VAT 0% EU M.
                    21M       => 21% M , 21% EU M, 21% M.Cocont and 21% EX M.
                    21" M"    => 21% M and 21% M.Cocont.
                    21" M"co  => 21% M.Cocont.
        """
        regex = r"(\"[^\"]*\")"
        list_name = re.split(regex, name)
        for i, name in enumerate(list_name.copy()):
            if not name:
                continue
            if re.search(regex, name):
                list_name[i] = "%" + name.replace("%", "_").replace("\"", "") + "%"
            else:
                list_name[i] = '%'.join(re.sub(r"\W+", "", name))
        return ''.join(list_name)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator in ("ilike", "like"):
            name = AccountTax._parse_name_search(name)
        return super()._name_search(name, args, operator, limit, name_get_uid)

    def _search_name(self, operator, value):
        if operator not in ("ilike", "like") or not isinstance(value, str):
            return [('name', operator, value)]
        return [('name', operator, AccountTax._parse_name_search(value))]

    def _check_repartition_lines(self, lines):
        self.ensure_one()

        base_line = lines.filtered(lambda x: x.repartition_type == 'base')
        if len(base_line) != 1:
            raise ValidationError(_("Invoice and credit note distribution should each contain exactly one line for the base."))

    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids')
    def _validate_repartition_lines(self):
        for record in self:
            # if the tax is an aggregation of its sub-taxes (group) it can have no repartition lines
            if record.amount_type == 'group' and \
                    not record.invoice_repartition_line_ids and \
                    not record.refund_repartition_line_ids:
                continue

            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted()
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted()
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(_("Invoice and credit note distribution should have the same number of lines."))

            if not invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax') or \
                    not refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax'):
                raise ValidationError(_("Invoice and credit note repartition should have at least one tax repartition line."))

            index = 0
            while index < len(invoice_repartition_line_ids):
                inv_rep_ln = invoice_repartition_line_ids[index]
                ref_rep_ln = refund_repartition_line_ids[index]
                if inv_rep_ln.repartition_type != ref_rep_ln.repartition_type or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent:
                    raise ValidationError(_("Invoice and credit note distribution should match (same percentages, in the same order)."))
                index += 1

    @api.constrains('children_tax_ids', 'type_tax_use')
    def _check_children_scope(self):
        for tax in self:
            if not tax._check_m2m_recursion('children_tax_ids'):
                raise ValidationError(_("Recursion found for tax '%s'.") % (tax.name,))
            if any(child.type_tax_use not in ('none', tax.type_tax_use) or child.tax_scope != tax.tax_scope for child in tax.children_tax_ids):
                raise ValidationError(_('The application scope of taxes in a group must be either the same as the group or left empty.'))

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if not self:
            return

        self.env['account.move.line'].flush_model(['company_id', 'tax_line_id'])
        self.flush_recordset(['company_id'])
        self._cr.execute('''
            SELECT line.id
            FROM account_move_line line
            JOIN account_tax tax ON tax.id = line.tax_line_id
            WHERE line.tax_line_id IN %s
            AND line.company_id != tax.company_id

            UNION ALL

            SELECT line.id
            FROM account_move_line_account_tax_rel tax_rel
            JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
            JOIN account_move_line line ON line.id = tax_rel.account_move_line_id
            WHERE tax_rel.account_tax_id IN %s
            AND line.company_id != tax.company_id
        ''', [tuple(self.ids)] * 2)
        if self._cr.fetchone():
            raise UserError(_("You can't change the company of your tax since there are some journal items linked to it."))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (Copy)") % self.name
        return super(AccountTax, self).copy(default=default)

    def name_get(self):
        name_list = []
        type_tax_use = dict(self._fields['type_tax_use']._description_selection(self.env))
        tax_scope = dict(self._fields['tax_scope']._description_selection(self.env))
        for record in self:
            name = record.name
            if self._context.get('append_type_to_tax_name'):
                name += ' (%s)' % type_tax_use.get(record.type_tax_use)
            if record.tax_scope:
                name += ' (%s)' % tax_scope.get(record.tax_scope)
            name_list += [(record.id, name)]
        return name_list

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        context = self._context or {}

        if context.get('move_type'):
            if context.get('move_type') in ('out_invoice', 'out_refund'):
                args += [('type_tax_use', '=', 'sale')]
            elif context.get('move_type') in ('in_invoice', 'in_refund'):
                args += [('type_tax_use', '=', 'purchase')]

        if context.get('journal_id'):
            journal = self.env['account.journal'].browse(context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += [('type_tax_use', '=', journal.type)]

        return super(AccountTax, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount_type in ('percent', 'division') and self.amount != 0.0 and not self.description:
            self.description = "{0:.4g}%".format(self.amount)

    @api.onchange('amount_type')
    def onchange_amount_type(self):
        if self.amount_type != 'group':
            self.children_tax_ids = [(5,)]
        if self.amount_type == 'group':
            self.description = None

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    @api.depends('invoice_repartition_line_ids', 'amount', 'invoice_repartition_line_ids.factor')
    def _compute_real_amount(self):
        for tax in self:
            tax_repartition_lines = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
            total_factor = sum(tax_repartition_lines.mapped('factor'))
            tax.real_amount = tax.amount * total_factor

    @api.model
    def _prepare_taxes_batches(self, tax_values_list):
        batches = []

        def batch_key(tax):
            return tax.amount_type, tax_values['price_include']

        def append_batch(batch):
            batch['taxes'] = list(reversed(batch['taxes']))
            batches.append(batch)

        current_batch = None
        is_base_affected = None
        for tax_values in reversed(tax_values_list):
            tax = tax_values['tax']

            if current_batch is not None:
                force_new_batch = (tax.include_base_amount and is_base_affected)
                if current_batch['key'] != batch_key(tax) or force_new_batch:
                    append_batch(current_batch)
                    current_batch = None

            if current_batch is None:
                current_batch = {
                    'key': batch_key(tax),
                    'taxes': [],
                    'amount_type': tax.amount_type,
                    'include_base_amount': tax.include_base_amount,
                    'price_include': tax_values['price_include'],
                }

            is_base_affected = tax.is_base_affected
            current_batch['taxes'].append(tax_values)

        if current_batch is not None:
            append_batch(current_batch)

        return batches

    @api.model
    def _ascending_process_fixed_taxes_batch(self, batch, base, precision_rounding, extra_computation_values, fixed_multiplicator=1):
        if batch['amount_type'] == 'fixed':
            batch['computed'] = True
            quantity = abs(extra_computation_values['quantity'])
            for tax_values in batch['taxes']:
                tax_values['tax_amount'] = quantity * tax_values['tax'].amount * abs(fixed_multiplicator)
                tax_values['tax_amount_factorized'] = float_round(
                    tax_values['tax_amount'] * tax_values['factor'],
                    precision_rounding=precision_rounding,
                )

    @api.model
    def _descending_process_price_included_taxes_batch(self, batch, base, precision_rounding, extra_computation_values):
        tax_values_list = batch['taxes']
        amount_type = batch['amount_type']
        price_include = batch['price_include']

        if price_include:
            if amount_type == 'percent':
                batch['computed'] = True
                total_percent = sum(
                    tax_values['tax'].amount * tax_values['factor']
                    for tax_values in tax_values_list
                ) / 100.0
                computation_base = base / (1 + total_percent)
                for tax_values in tax_values_list:
                    tax_values['tax_amount'] = computation_base * tax_values['tax'].amount / 100.0
                    tax_values['tax_amount_factorized'] = float_round(
                        tax_values['tax_amount'] * tax_values['factor'],
                        precision_rounding=precision_rounding,
                    )

                batch_base = base - sum(tax_values['tax_amount_factorized'] for tax_values in tax_values_list)
                for tax_values in tax_values_list:
                    tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = batch_base

            elif amount_type == 'division':
                batch['computed'] = True
                batch_base = base

                for tax_values in tax_values_list:
                    tax = tax_values['tax']
                    not_factorized_base = base * (1 - (tax_values['tax'].amount * tax_values['factor'] / 100.0))
                    tax_values['tax_amount'] = base - not_factorized_base
                    tax_values['tax_amount_factorized'] = float_round(
                        tax_values['tax_amount'] * tax_values['factor'],
                        precision_rounding=precision_rounding,
                    )
                    tax_values['base'] = base - tax_values['tax_amount_factorized']
                    batch_base -= tax_values['tax_amount_factorized']

                grouping_key_base = defaultdict(lambda: base)
                for tax_values in tax_values_list:
                    grouping_key_base[tax_values['grouping_key']] -= tax_values['tax_amount_factorized']
                for tax_values in tax_values_list:
                    tax_values['grouping_base'] = grouping_key_base[tax_values['grouping_key']]
                    tax_values['batch_base'] = batch_base

            elif amount_type == 'fixed':
                for tax_values in tax_values_list:
                    tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = base

    @api.model
    def _ascending_process_taxes_batch(self, batch, base, precision_rounding, extra_computation_values):
        tax_values_list = batch['taxes']
        amount_type = tax_values_list[0]['tax'].amount_type
        price_include = batch['price_include']

        if not price_include:

            if amount_type == 'percent':
                batch['computed'] = True
                for tax_values in tax_values_list:
                    tax_values['tax_amount'] = base * tax_values['tax'].amount / 100.0
                    tax_values['tax_amount_factorized'] = float_round(
                        tax_values['tax_amount'] * tax_values['factor'],
                        precision_rounding=precision_rounding,
                    )
                    tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = base

            elif amount_type == 'division':
                batch['computed'] = True
                for tax_values in tax_values_list:
                    base_tax_included = base / (1 - (tax_values['tax'].amount / 100.0))
                    tax_values['tax_amount'] = base_tax_included - base
                    tax_values['tax_amount_factorized'] = float_round(
                        tax_values['tax_amount'] * tax_values['factor'],
                        precision_rounding=precision_rounding,
                    )
                    tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = base

            elif amount_type == 'fixed':
                batch['computed'] = True
                quantity = abs(extra_computation_values['quantity'])
                for tax_values in tax_values_list:
                    tax_values['tax_amount'] = quantity * tax_values['tax'].amount
                    tax_values['tax_amount_factorized'] = float_round(
                        tax_values['tax_amount'] * tax_values['factor'],
                        precision_rounding=precision_rounding,
                    )
                    tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = base

    @api.model
    def _prepare_tax_repartition_line_results(self, tax_values, currency, precision_rounding):
        repartition_line_amounts = [
            float_round(tax_values['tax_amount'] * line.factor, precision_rounding=precision_rounding)
            for line in tax_values['repartition_lines']
        ]
        total_rounding_error = float_round(
            tax_values['tax_amount_factorized'] - sum(repartition_line_amounts),
            precision_rounding=precision_rounding,
        )
        nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
        rounding_error = float_round(
            total_rounding_error / nber_rounding_steps if nber_rounding_steps else 0.0,
            precision_rounding=precision_rounding,
        )

        tax_repartition_values_list = []
        for repartition_line, line_amount in zip(tax_values['repartition_lines'], repartition_line_amounts):

            if nber_rounding_steps:
                line_amount += rounding_error
                nber_rounding_steps -= 1

            tax_repartition_values_list.append({
                'tax_amount': line_amount,
                'repartition_line': repartition_line,
            })
        return tax_repartition_values_list

    def json_friendly_compute_all(self, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None, is_refund=False, include_caba_tags=False):
        """ Called by the reconciliation to compute taxes on writeoff during bank reconciliation
        """
        if currency_id:
            currency_id = self.env['res.currency'].browse(currency_id)
        if product_id:
            product_id = self.env['product.product'].browse(product_id)
        if partner_id:
            partner_id = self.env['res.partner'].browse(partner_id)

        # We first need to find out whether this tax computation is made for a refund
        tax_type = self and self[0].type_tax_use
        is_refund = is_refund or (tax_type == 'sale' and price_unit > 0) or (tax_type == 'purchase' and price_unit < 0)

        rslt = self.with_context(caba_no_transition_account=True)\
                   .compute_all(price_unit, currency=currency_id, quantity=quantity, product=product_id, partner=partner_id, is_refund=is_refund, include_caba_tags=include_caba_tags)

        return rslt

    def flatten_taxes_hierarchy(self, create_map=False):
        # Flattens the taxes contained in this recordset, returning all the
        # children at the bottom of the hierarchy, in a recordset, ordered by sequence.
        #   Eg. considering letters as taxes and alphabetic order as sequence :
        #   [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        # If create_map is True, an additional value is returned, a dictionary
        # mapping each child tax to its parent group
        all_taxes = self.env['account.tax']
        groups_map = {}
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                flattened_children = tax.children_tax_ids.flatten_taxes_hierarchy()
                all_taxes += flattened_children
                for flat_child in flattened_children:
                    groups_map[flat_child] = tax
            else:
                all_taxes += tax

        if create_map:
            return all_taxes, groups_map

        return all_taxes

    def get_tax_tags(self, is_refund, repartition_type):
        rep_lines = self.mapped(is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids')
        return rep_lines.filtered(lambda x: x.repartition_type == repartition_type).mapped('tag_ids')

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1, grouping_key_generator=None):
        """Compute all information required to apply taxes (in self + their children in case of a tax group).
        We consider the sequence of the parent for group of taxes.
            Eg. considering letters as taxes and alphabetic order as sequence :
            [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]



        :param price_unit: The unit price of the line to compute taxes on.
        :param currency: The optional currency in which the price_unit is expressed.
        :param quantity: The optional quantity of the product to compute taxes on.
        :param product: The optional product to compute taxes on.
            Used to get the tags to apply on the lines.
        :param partner: The optional partner compute taxes on.
            Used to retrieve the lang to build strings and for potential extensions.
        :param is_refund: The optional boolean indicating if this is a refund.
        :param handle_price_include: Used when we need to ignore all tax included in price. If False, it means the
            amount passed to this method will be considered as the base of all computations.
        :param include_caba_tags: The optional boolean indicating if CABA tags need to be taken into account.
        :param fixed_multiplicator: The amount to multiply fixed amount taxes by.
        :return: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'total_void'    : 0.0,    # Total with those taxes, that don't have an account set
            'base_tags: : list<int>,  # Tags to apply on the base line
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'base': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': bool,
                'price_include': bool,
                'tax_exigibility': str,
                'tax_repartition_line_id': int,
                'group': recordset,
                'tag_ids': list<int>,
                'tax_ids': list<int>,
            }],
        } """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        # 1) Flatten the taxes.
        taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)

        # 2) Deal with the rounding methods
        if not currency:
            currency = company.currency_id

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.rounding

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec *= 1e-5

        # 3) Prepare initial values.
        base = currency.round(price_unit * quantity)

        # We could have a negative base value.
        # In this case, compute all with positive values and negate them at the end.
        sign = 1
        if currency.is_zero(base):
            sign = -1 if fixed_multiplicator < 0 else 1
        elif base < 0:
            sign = -1
            base = -base

        if is_refund:
            repartition_lines_field = 'refund_repartition_line_ids'
        else:
            repartition_lines_field = 'invoice_repartition_line_ids'

        tax_values_list = []
        for tax in taxes:
            tax_values = {
                'tax': tax,
                'price_include': handle_price_include and (tax.price_include or self._context.get('force_price_include')),
                'repartition_lines': tax[repartition_lines_field].filtered(lambda x: x.repartition_type == "tax"),
            }
            tax_values['factor'] = sum(tax_values['repartition_lines'].mapped('factor'))
            grouping_key = grouping_key_generator(tax_values) if grouping_key_generator else {}
            tax_values['grouping_key'] = frozendict(grouping_key)
            tax_values_list.append(tax_values)

        # 4) Process batches.
        if product and product._name == 'product.template':
            product = product.product_variant_id

        extra_computation_values = {
            'price_unit': price_unit,
            'quantity': quantity,
            'product': product,
            'partner': partner,
            'fixed_multiplicator': fixed_multiplicator,
            'company': company,
        }

        descending_batches = self._prepare_taxes_batches(tax_values_list)
        ascending_batches = list(reversed(descending_batches))

        # First ascending computation for fixed tax.
        # In Belgium, we could have a price-excluded tax affecting the base of a price-included tax.
        # In that case, we need to compute the fix amount before the descending computation.
        extra_base = 0.0
        for batch in ascending_batches:
            batch['extra_base'] = extra_base
            self._ascending_process_fixed_taxes_batch(batch, base, prec, extra_computation_values, fixed_multiplicator=fixed_multiplicator)
            if batch.get('computed'):
                batch.pop('computed')
                if batch['include_base_amount']:
                    extra_base += sum(tax_values['tax_amount_factorized'] for tax_values in batch['taxes'])

        # First descending computation to compute price_included values and find the total_excluded amount.
        for batch in descending_batches:
            self._descending_process_price_included_taxes_batch(batch, base + batch['extra_base'], prec, extra_computation_values)
            if batch.get('computed'):
                base -= sum(tax_values['tax_amount_factorized'] for tax_values in batch['taxes'])

        # Product tags needs to be added to tax_tag_ids as well.
        product_tag_ids = product.account_tag_ids.ids if product else []

        # Second ascending computation to compute the missing values for price-excluded taxes.
        # Split the amounts according the tax repartition lines and build the final results.
        total_included = total_void = total_excluded = base
        lines_results = []
        for i, batch in enumerate(ascending_batches):
            self._ascending_process_taxes_batch(batch, base, prec, extra_computation_values)

            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if batch['include_base_amount']:
                base += sum(tax_values['tax_amount_factorized'] for tax_values in batch['taxes'])

                for next_batch in ascending_batches[i + 1:]:
                    for next_tax_values in next_batch['taxes']:
                        subsequent_taxes |= next_tax_values['tax']

                taxes_for_subsequent_tags = subsequent_taxes
                if not include_caba_tags:
                    taxes_for_subsequent_tags = subsequent_taxes.filtered(lambda x: x.tax_exigibility != 'on_payment')
                subsequent_tags = taxes_for_subsequent_tags.get_tax_tags(is_refund, 'base')

            for tax_values in batch['taxes']:
                tax = tax_values['tax']

                tax_repartition_values_list = self._prepare_tax_repartition_line_results(
                    tax_values,
                    currency,
                    prec,
                )
                for tax_repartition_values in tax_repartition_values_list:
                    repartition_line = tax_repartition_values['repartition_line']

                    if not include_caba_tags and tax.tax_exigibility == 'on_payment':
                        repartition_line_tags = self.env['account.account.tag']
                    else:
                        repartition_line_tags = repartition_line.tag_ids

                    lines_results.append({
                        'id': tax.id,
                        'name': tax.with_context(lang=partner.lang).name if partner else tax.name,
                        'amount': sign * tax_repartition_values['tax_amount'],
                        'base': float_round(sign * tax_values['base'], precision_rounding=prec),
                        'grouping_key': tax_values['grouping_key'],
                        'grouping_base': float_round(sign * tax_values['grouping_base'], precision_rounding=prec),
                        'batch_base': float_round(sign * tax_values['batch_base'], precision_rounding=prec),
                        'sequence': tax.sequence,
                        'account_id': repartition_line._get_aml_target_tax_account(force_caba_exigibility=include_caba_tags).id,
                        'analytic': tax.analytic,
                        'use_in_tax_closing': repartition_line.use_in_tax_closing,
                        'price_include': batch['price_include'],
                        'tax_exigibility': tax.tax_exigibility,
                        'tax_repartition_line_id': repartition_line.id,
                        'group': groups_map.get(tax),
                        'tag_ids': (repartition_line_tags + subsequent_tags).ids + product_tag_ids,
                        'tax_ids': subsequent_taxes.ids,
                    })

                    if not repartition_line.account_id:
                        total_void += tax_repartition_values['tax_amount']
                    total_included += tax_repartition_values['tax_amount']

        base_taxes_for_tags = taxes
        if not include_caba_tags:
            base_taxes_for_tags = base_taxes_for_tags.filtered(lambda x: x.tax_exigibility != 'on_payment')

        base_rep_lines = base_taxes_for_tags \
            .mapped(repartition_lines_field) \
            .filtered(lambda x: x.repartition_type == 'base')

        return {
            'base_tags': base_rep_lines.tag_ids.ids + product_tag_ids,
            'taxes': lines_results,
            'total_excluded': sign * currency.round(total_excluded),
            'total_included': sign * currency.round(total_included),
            'total_void': sign * currency.round(total_void),
        }

    @api.model
    def _convert_to_tax_base_line_dict(
            self, base_line,
            partner=None, currency=None, product=None, taxes=None, price_unit=None, quantity=None,
            discount=None, account=None, analytic_distribution=None, price_subtotal=None,
            is_refund=False, rate=None,
            handle_price_include=True,
            extra_context=None,
    ):
        return {
            'record': base_line,
            'partner': partner or self.env['res.partner'],
            'currency': currency or self.env['res.currency'],
            'product': product or self.env['product.product'],
            'taxes': taxes or self.env['account.tax'],
            'price_unit': price_unit or 0.0,
            'quantity': quantity or 0.0,
            'discount': discount or 0.0,
            'account': account or self.env['account.account'],
            'analytic_distribution': analytic_distribution,
            'price_subtotal': price_subtotal or 0.0,
            'is_refund': is_refund,
            'rate': rate or 1.0,
            'handle_price_include': handle_price_include,
            'extra_context': extra_context or {},
        }

    @api.model
    def _convert_to_tax_line_dict(
            self, tax_line,
            partner=None, currency=None, taxes=None, tax_tags=None, tax_repartition_line=None,
            group_tax=None, account=None, analytic_distribution=None, tax_amount=None,
    ):
        return {
            'record': tax_line,
            'partner': partner or self.env['res.partner'],
            'currency': currency or self.env['res.currency'],
            'taxes': taxes or self.env['account.tax'],
            'tax_tags': tax_tags or self.env['account.account.tag'],
            'tax_repartition_line': tax_repartition_line or self.env['account.tax.repartition.line'],
            'group_tax': group_tax or self.env['account.tax'],
            'account': account or self.env['account.account'],
            'analytic_distribution': analytic_distribution,
            'tax_amount': tax_amount or 0.0,
        }

    @api.model
    def _get_generation_dict_from_base_line(self, line_vals, tax_vals, force_caba_exigibility=False):
        """ Take a tax results returned by the taxes computation method and return a dictionary representing the way
        the tax amounts will be grouped together. To do so, the dictionary will be converted into a string key.
        Then, the existing tax lines sharing the same key will be updated and the missing ones will be created.

        :param line_vals:   A python dict returned by '_convert_to_tax_base_line_dict'.
        :param tax_vals:    A python dict returned by 'compute_all' under the 'taxes' key.
        :return:            A python dict.
        """
        tax_repartition_line = tax_vals['tax_repartition_line']
        tax_account = tax_repartition_line._get_aml_target_tax_account(force_caba_exigibility=force_caba_exigibility) or line_vals['account']
        return {
            'account_id': tax_account.id,
            'currency_id': line_vals['currency'].id,
            'partner_id': line_vals['partner'].id,
            'tax_repartition_line_id': tax_repartition_line.id,
            'tax_ids': [Command.set(tax_vals['tax_ids'])],
            'tax_tag_ids': [Command.set(tax_vals['tag_ids'])],
            'tax_id': tax_vals['group'].id if tax_vals['group'] else tax_vals['id'],
            'analytic_distribution': line_vals['analytic_distribution'] if tax_vals['analytic'] else {},
        }

    @api.model
    def _get_generation_dict_from_tax_line(self, line_vals):
        """ Turn the values corresponding to a tax line and convert it into a dictionary. The dictionary will be
        converted into a string key. This allows updating the existing tax lines instead of creating new ones
        everytime.

        :param line_vals:   A python dict returned by '_convert_to_tax_line_dict'.
        :return:            A python dict representing the grouping key used to update an existing tax line.
        """
        tax = line_vals['tax_repartition_line'].tax_id
        return {
            'account_id': line_vals['account'].id,
            'currency_id': line_vals['currency'].id,
            'partner_id': line_vals['partner'].id,
            'tax_repartition_line_id': line_vals['tax_repartition_line'].id,
            'tax_ids': [Command.set(line_vals['taxes'].ids)],
            'tax_tag_ids': [Command.set(line_vals['tax_tags'].ids)],
            'tax_id': (line_vals['group_tax'] or tax).id,
            'analytic_distribution': line_vals['analytic_distribution'] if tax.analytic else {},
        }

    @api.model
    def _compute_taxes_for_single_line(
        self,
        base_line,
        handle_price_include=True,
        include_caba_tags=False,
        early_pay_discount_computation=None,
        early_pay_discount_percentage=None,
        grouping_key_generator=None,
    ):
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']

        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:
            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=base_line['handle_price_include'],
                include_caba_tags=include_caba_tags,
                grouping_key_generator=grouping_key_generator,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=base_line['handle_price_include'],
                    include_caba_tags=include_caba_tags,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                tax_values_list.append({
                    **tax_res,
                    'tax_repartition_line': tax_rep,
                    'base_amount_currency': tax_res['base'],
                    'base_amount': currency.round(tax_res['base'] / rate),
                    'grouping_base_amount_currency': tax_res['grouping_base'],
                    'grouping_base_amount': currency.round(tax_res['grouping_base'] / rate),
                    'batch_base_amount_currency': tax_res['batch_base'],
                    'batch_base_amount': currency.round(tax_res['batch_base'] / rate),
                    'tax_amount_currency': tax_res['amount'],
                    'tax_amount': tax_amount,
                })

        else:
            price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list

    @api.model
    def _aggregate_taxes(self, to_process, filter_tax_values_to_apply=None, grouping_key_generator=None):

        global_tax_details = {
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
            'tax_details': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'group_tax_details': [],
                'records': set(),
            }),
            'tax_details_per_record': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'tax_details': defaultdict(lambda: {
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'group_tax_details': [],
                    'records': set(),
                }),
            }),
        }

        if self.env.company.tax_calculation_rounding_method == 'round_globally':
            amount_per_tax_repartition_line_id = defaultdict(lambda: {
                'delta_tax_amount': 0.0,
                'delta_tax_amount_currency': 0.0,
            })
            for base_line, to_update_vals, tax_values_list in to_process:
                currency = base_line['currency'] or self.env.company.currency_id
                comp_currency = self.env.company.currency_id
                for tax_values in tax_values_list:
                    grouping_key = frozendict(self._get_generation_dict_from_base_line(base_line, tax_values))

                    total_amounts = amount_per_tax_repartition_line_id[grouping_key]
                    tax_amount_currency_with_delta = tax_values['tax_amount_currency'] \
                                                     + total_amounts['delta_tax_amount_currency']
                    tax_amount_currency = currency.round(tax_amount_currency_with_delta)
                    tax_amount_with_delta = tax_values['tax_amount'] \
                                            + total_amounts['delta_tax_amount']
                    tax_amount = comp_currency.round(tax_amount_with_delta)
                    tax_values['tax_amount_currency'] = tax_amount_currency
                    tax_values['tax_amount'] = tax_amount
                    total_amounts['delta_tax_amount_currency'] = tax_amount_currency_with_delta - tax_amount_currency
                    total_amounts['delta_tax_amount'] = tax_amount_with_delta - tax_amount

        for base_line, to_update_vals, tax_values_list in to_process:
            record = base_line['record']

            seen_grouping_keys = set()
            base_added = False
            for tax_values in tax_values_list:

                for results in (global_tax_details, global_tax_details['tax_details_per_record'][record]):
                    local_results = results['tax_details'][tax_values['grouping_key']]
                    if not base_added:
                        base_added = True
                        results['base_amount_currency'] += tax_values['batch_base_amount_currency']
                        results['base_amount'] += tax_values['batch_base_amount']
                    if tax_values['grouping_key'] not in seen_grouping_keys:
                        local_results['base_amount_currency'] += tax_values['grouping_base_amount_currency']
                        local_results['base_amount'] += tax_values['grouping_base_amount']
                        local_results.update(tax_values['grouping_key'])
                        local_results['records'].add(record)
                        local_results['group_tax_details'].append(tax_values)

                    results['tax_amount_currency'] += tax_values['tax_amount_currency']
                    results['tax_amount'] += tax_values['tax_amount']
                    local_results['tax_amount_currency'] += tax_values['tax_amount_currency']
                    local_results['tax_amount'] += tax_values['tax_amount']

                seen_grouping_keys.add(tax_values['grouping_key'])

        return global_tax_details

    @api.model
    def _compute_taxes(self, base_lines, tax_lines=None, handle_price_include=True, include_caba_tags=False):
        """ Generic method to compute the taxes for different business models.

        :param base_lines: A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param tax_lines: A list of python dictionaries created using the '_convert_to_tax_line_dict' method.
        :param handle_price_include:    Manage the price-included taxes. If None, use the 'handle_price_include' key
                                        set on base lines.
        :param include_caba_tags: Manage tags for taxes being exigible on_payment.
        :return: A python dictionary containing:

            The complete diff on tax lines if 'tax_lines' is passed as parameter:
            * tax_lines_to_add:     To create new tax lines.
            * tax_lines_to_delete:  To track the tax lines that are no longer used.
            * tax_lines_to_update:  The values to update the existing tax lines.

            * base_lines_to_update: The values to update the existing base lines:
                * tax_tag_ids:          The tags related to taxes.
                * price_subtotal:       The amount without tax.
                * price_total:          The amount with taxes.

            * totals:               A mapping for each involved currency to:
                * amount_untaxed:       The base amount without tax.
                * amount_tax:           The total tax amount.
        """
        res = {
            'tax_lines_to_add': [],
            'tax_lines_to_delete': [],
            'tax_lines_to_update': [],
            'base_lines_to_update': [],
            'totals': defaultdict(lambda: {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
            }),
        }

        # =========================================================================================
        # BASE LINES
        # For each base line, populate 'base_lines_to_update'.
        # Compute 'tax_base_amount'/'tax_amount' for each pair <base line, tax repartition line>
        # using the grouping key generated by the '_get_generation_dict_from_base_line' method.
        # =========================================================================================

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(
                base_line,
                include_caba_tags=include_caba_tags,
            )
            to_process.append((base_line, to_update_vals, tax_values_list))
            res['base_lines_to_update'].append((base_line, to_update_vals))
            currency = base_line['currency'] or self.env.company.currency_id
            res['totals'][currency]['amount_untaxed'] += to_update_vals['price_subtotal']

        # =========================================================================================
        # TAX LINES
        # Map each existing tax lines using the grouping key generated by the
        # '_get_generation_dict_from_tax_line' method.
        # Since everything is indexed using the grouping key, we are now able to decide if
        # (1) we can reuse an existing tax line and update its amounts
        # (2) some tax lines are no longer used and can be dropped
        # (3) we need to create new tax lines
        # =========================================================================================

        # Track the existing tax lines using the grouping key.
        existing_tax_line_map = {}
        for line_vals in tax_lines or []:
            grouping_key = frozendict(self._get_generation_dict_from_tax_line(line_vals))

            # After a modification (e.g. changing the analytic account of the tax line), if two tax lines are sharing
            # the same key, keep only one.
            if grouping_key in existing_tax_line_map:
                res['tax_lines_to_delete'].append(line_vals)
            else:
                existing_tax_line_map[grouping_key] = line_vals

        def grouping_key_generator(base_line, tax_values):
            return self._get_generation_dict_from_base_line(base_line, tax_values, force_caba_exigibility=include_caba_tags)

        # Update/create the tax lines.
        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        for grouping_key, tax_values in global_tax_details['tax_details'].items():
            if tax_values['currency_id']:
                currency = self.env['res.currency'].browse(tax_values['currency_id'])
                tax_amount = currency.round(tax_values['tax_amount'])
                res['totals'][currency]['amount_tax'] += tax_amount

            if grouping_key in existing_tax_line_map:
                # Update an existing tax line.
                line_vals = existing_tax_line_map.pop(grouping_key)
                res['tax_lines_to_update'].append((line_vals, tax_values))
            else:
                # Create a new tax line.
                res['tax_lines_to_add'].append(tax_values)

        for line_vals in existing_tax_line_map.values():
            res['tax_lines_to_delete'].append(line_vals)

        return res

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None):
        """ Compute the tax totals details for the business documents.
        :param base_lines:  A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:    The currency set on the business document.
        :param tax_lines:   Optional list of python dictionaries created using the '_convert_to_tax_line_dict' method.
                            If specified, the taxes will be recomputed using them instead of recomputing the taxes on
                            the provided base lines.
        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                   The name of the tax groups this total is made for.
                        'tax_group_amount':                 The total tax amount in this tax group.
                        'tax_group_base_amount':            The base amount for this tax group.
                        'formatted_tax_group_amount':       Same as tax_group_amount, but as a string formatted accordingly
                                                            with partner's locale.
                        'formatted_tax_group_base_amount':  Same as tax_group_base_amount, but as a string formatted
                                                            accordingly with partner's locale.
                        'tax_group_id':                     The id of the tax group corresponding to this dict.
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                    }
                'subtotals_order':              A list of keys of `groups_by_subtotals` defining the order in which it needs
                                                to be displayed
            }
        """

        # ==== Compute the taxes ====

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(
                base_line,
                grouping_key_generator=lambda tax_values: {'tax_group': tax_values['tax'].tax_group_id},
            )
            to_process.append((base_line, to_update_vals, tax_values_list))

        global_tax_details = self._aggregate_taxes(to_process)

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
            }

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
            })

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax

        display_tax_base = (len(global_tax_details['tax_details']) == 1 and currency.compare_amounts(tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0)\
                           or len(global_tax_details['tax_details']) > 1

        return {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        """Subtract tax amount from price when corresponding "price included" taxes do not apply"""
        # FIXME get currency in param?
        prod_taxes = prod_taxes._origin
        line_taxes = line_taxes._origin
        incl_tax = prod_taxes.filtered(lambda tax: tax not in line_taxes and tax.price_include)
        if incl_tax:
            return incl_tax.compute_all(price)['total_excluded']
        return price

    @api.model
    def _fix_tax_included_price_company(self, price, prod_taxes, line_taxes, company_id):
        if company_id:
            #To keep the same behavior as in _compute_tax_id
            prod_taxes = prod_taxes.filtered(lambda tax: tax.company_id == company_id)
            line_taxes = line_taxes.filtered(lambda tax: tax.company_id == company_id)
        return self._fix_tax_included_price(price, prod_taxes, line_taxes)


class AccountTaxRepartitionLine(models.Model):
    _name = "account.tax.repartition.line"
    _description = "Tax Repartition Line"
    _order = 'sequence, repartition_type, id'
    _check_company_auto = True

    factor_percent = fields.Float(
        string="%",
        default=100,
        required=True,
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the account move lines generated from this distribution line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        check_company=True,
        help="Account on which to post the tax amount")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True, ondelete='restrict')
    invoice_tax_id = fields.Many2one(comodel_name='account.tax',
        ondelete='cascade',
        check_company=True,
        help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax',
        ondelete='cascade',
        check_company=True,
        help="The tax set to apply this distribution on refund invoices. Mutually exclusive with invoice_tax_id")
    tax_id = fields.Many2one(comodel_name='account.tax', compute='_compute_tax_id')
    document_type = fields.Selection(
        selection=[
            ('invoice', 'Invoice'),
            ('refund', 'Refund'),
        ],
        compute='_compute_document_type',
        help="The type of documnet on which the repartition line should be applied",
    )
    company_id = fields.Many2one(string="Company", comodel_name='res.company', compute="_compute_company", store=True, help="The company this distribution line belongs to.")
    sequence = fields.Integer(string="Sequence", default=1,
        help="The order in which distribution lines are displayed and matched. For refunds to work properly, invoice distribution lines should be arranged in the same order as the credit note distribution lines they correspond to.")
    use_in_tax_closing = fields.Boolean(string="Tax Closing Entry", default=True)

    tag_ids_domain = fields.Binary(string="tag domain", help="Dynamic domain used for the tag that can be set on tax", compute="_compute_tag_ids_domain")

    @api.depends('company_id.multi_vat_foreign_country_ids', 'company_id.account_fiscal_country_id')
    def _compute_tag_ids_domain(self):
        for rep_line in self:
            allowed_country_ids = (False, rep_line.company_id.account_fiscal_country_id.id, *rep_line.company_id.multi_vat_foreign_country_ids.ids,)
            rep_line.tag_ids_domain = [('applicability', '=', 'taxes'), ('country_id', 'in', allowed_country_ids)]

    @api.onchange('account_id', 'repartition_type')
    def _on_change_account_id(self):
        if not self.account_id or self.repartition_type == 'base':
            self.use_in_tax_closing = False
        else:
            self.use_in_tax_closing = self.account_id.internal_group not in ('income', 'expense')

    @api.constrains('invoice_tax_id', 'refund_tax_id')
    def validate_tax_template_link(self):
        for record in self:
            if record.invoice_tax_id and record.refund_tax_id:
                raise ValidationError(_("Tax distribution lines should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

    @api.depends('factor_percent')
    def _compute_factor(self):
        for record in self:
            record.factor = record.factor_percent / 100.0

    @api.depends('invoice_tax_id.company_id', 'refund_tax_id.company_id')
    def _compute_company(self):
        for record in self:
            record.company_id = record.invoice_tax_id and record.invoice_tax_id.company_id.id or record.refund_tax_id.company_id.id

    @api.depends('invoice_tax_id', 'refund_tax_id')
    def _compute_tax_id(self):
        for record in self:
            record.tax_id = record.invoice_tax_id or record.refund_tax_id

    @api.depends('invoice_tax_id', 'refund_tax_id')
    def _compute_document_type(self):
        for record in self:
            record.document_type = 'invoice' if record.invoice_tax_id else 'refund'

    @api.onchange('repartition_type')
    def _onchange_repartition_type(self):
        if self.repartition_type == 'base':
            self.account_id = None

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        """ Get the default tax account to set on a business line.

        :return: An account.account record or an empty recordset.
        """
        self.ensure_one()
        if not force_caba_exigibility and self.tax_id.tax_exigibility == 'on_payment' and not self._context.get('caba_no_transition_account'):
            return self.tax_id.cash_basis_transition_account_id
        else:
            return self.account_id
