# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError

import math
import logging


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
    property_tax_payable_account_id = fields.Many2one('account.account', company_dependent=True, string='Tax current account (payable)')
    property_tax_receivable_account_id = fields.Many2one('account.account', company_dependent=True, string='Tax current account (receivable)')
    property_advance_tax_payment_account_id = fields.Many2one('account.account', company_dependent=True, string='Advance Tax payment account')

    def _any_is_configured(self, company_id):
        domain = expression.OR([[('property_tax_payable_account_id', '!=', False)],
                                [('property_tax_receivable_account_id', '!=', False)],
                                [('property_advance_tax_payment_account_id', '!=', False)]])
        group_with_config = self.with_company(company_id).search_count(domain)
        return group_with_config > 0


class AccountTax(models.Model):
    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence,id'
    _check_company_auto = True

    @api.model
    def _default_tax_group(self):
        return self.env['account.tax.group'].search([], limit=1)

    name = fields.Char(string='Tax Name', required=True)
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
    description = fields.Char(string='Label on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Base of Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    is_affected_former_tax = fields.Boolean(
        string="Is Affected by Former Tax",
        default=True,
        help="If set, taxes are affected by previous one that affect the base.")
    analytic = fields.Boolean(string="Include in Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    tax_group_id = fields.Many2one('account.tax.group', string="Tax Group", default=_default_tax_group, required=True)
    # Technical field to make the 'tax_exigibility' field invisible if the same named field is set to false in 'res.company' model
    hide_tax_exigibility = fields.Boolean(string='Hide Use Cash Basis Option', related='company_id.tax_exigibility', readonly=True)
    tax_exigibility = fields.Selection(
        [('on_invoice', 'Based on Invoice'),
         ('on_payment', 'Based on Payment'),
        ], string='Tax Due', default='on_invoice',
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
        "Based on Payment: the tax is due as soon as the payment of the invoice is received.")
    cash_basis_transition_account_id = fields.Many2one(string="Cash Basis Transition Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        comodel_name='account.account',
        help="Account used to transition the tax amount for cash basis taxes. It will contain the tax amount as long as the original invoice has not been reconciled ; at reconciliation, this amount cancelled on this account and put on the regular tax account.")
    invoice_repartition_line_ids = fields.One2many(string="Distribution for Invoices", comodel_name="account.tax.repartition.line", inverse_name="invoice_tax_id", copy=True, help="Distribution when the tax is used on an invoice")
    refund_repartition_line_ids = fields.One2many(string="Distribution for Refund Invoices", comodel_name="account.tax.repartition.line", inverse_name="refund_tax_id", copy=True, help="Distribution when the tax is used on a refund")
    tax_fiscal_country_id = fields.Many2one(string='Fiscal Country', comodel_name='res.country', related='company_id.account_tax_fiscal_country_id', help="Technical field used to restrict the domain of account tags for tax repartition lines created for this tax.")
    country_code = fields.Char(related='company_id.country_id.code', readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use, tax_scope)', 'Tax names must be unique !'),
    ]

    @api.model
    def default_get(self, fields_list):
        # company_id is added so that we are sure to fetch a default value from it to use in repartition lines, below
        rslt = super(AccountTax, self).default_get(fields_list + ['company_id'])

        company_id = rslt.get('company_id')
        company = self.env['res.company'].browse(company_id)

        if 'refund_repartition_line_ids' in fields_list:
            # We write on the related country_id field so that the field is recomputed. Without that, it will stay empty until we save the record.
            rslt['refund_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
            ]

        if 'invoice_repartition_line_ids' in fields_list:
            # We write on the related country_id field so that the field is recomputed. Without that, it will stay empty until we save the record.
            rslt['invoice_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'tax_fiscal_country_id': company.country_id.id}),
            ]

        return rslt

    def _check_repartition_lines(self, lines):
        self.ensure_one()

        base_line = lines.filtered(lambda x: x.repartition_type == 'base')
        if len(base_line) != 1:
            raise ValidationError(_("Invoice and credit note distribution should each contain exactly one line for the base."))

    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids')
    def _validate_repartition_lines(self):
        for record in self:
            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted()
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted()
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(_("Invoice and credit note distribution should have the same number of lines."))

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

        self.flush(['company_id'])
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
        default = dict(default or {}, name=_("%s (Copy)", self.name))
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
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """ Returns a list of tuples containing id, name, as internally it is called {def name_get}
            result format: {[(id, name), (id, name), ...]}
        """
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('description', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

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

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()

        if self.amount_type == 'fixed':
            # Use copysign to take into account the sign of the base amount which includes the sign
            # of the quantity and the sign of the price_unit
            # Amount is the fixed price for the tax, it can be negative
            # Base amount included the sign of the quantity and the sign of the unit price and when
            # a product is returned, it can be done either by changing the sign of quantity or by changing the
            # sign of the price unit.
            # When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
            # a "else" case is needed.
            if base_amount:
                return math.copysign(quantity, base_amount) * self.amount
            else:
                return quantity * self.amount

        price_include = self._context.get('force_price_include', self.price_include)

        # base * (1 + tax_amount) = new_base
        if self.amount_type == 'percent' and not price_include:
            return base_amount * self.amount / 100
        # <=> new_base = base / (1 + tax_amount)
        if self.amount_type == 'percent' and price_include:
            return base_amount - (base_amount / (1 + self.amount / 100))
        # base / (1 - tax_amount) = new_base
        if self.amount_type == 'division' and not price_include:
            return base_amount / (1 - self.amount / 100) - base_amount if (1 - self.amount / 100) else 0.0
        # <=> new_base * (1 - tax_amount) = base
        if self.amount_type == 'division' and price_include:
            return base_amount - (base_amount * (self.amount / 100))

    def json_friendly_compute_all(self, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None, is_refund=False):
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
        is_refund = is_refund or (tax_type == 'sale' and price_unit < 0) or (tax_type == 'purchase' and price_unit > 0)

        rslt = self.compute_all(price_unit, currency=currency_id, quantity=quantity, product=product_id, partner=partner_id, is_refund=is_refund)

        # The reconciliation widget calls this function to generate writeoffs on bank journals,
        # so the sign of the tags might need to be inverted, so that the tax report
        # computation can treat them as any other miscellaneous operations, while
        # keeping a computation in line with the effect the tax would have had on an invoice.

        if (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund):
            base_tags = self.env['account.account.tag'].browse(rslt['base_tags'])
            rslt['base_tags'] = self.env['account.move.line']._revert_signed_tags(base_tags).ids

            for tax_result in rslt['taxes']:
                tax_tags = self.env['account.account.tag'].browse(tax_result['tag_ids'])
                tax_result['tag_ids'] = self.env['account.move.line']._revert_signed_tags(tax_tags).ids

        return rslt

    def flatten_taxes_hierarchy(self):
        # Flattens the taxes contained in this recordset, returning all the
        # children at the bottom of the hierarchy, in a recordset, ordered by sequence.
        #   Eg. considering letters as taxes and alphabetic order as sequence :
        #   [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        all_taxes = self.env['account.tax']
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                all_taxes += tax.children_tax_ids.flatten_taxes_hierarchy()
            else:
                all_taxes += tax
        return all_taxes

    def get_tax_tags(self, is_refund, repartition_type):
        rep_lines = self.mapped(is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids')
        return rep_lines.filtered(lambda x: x.repartition_type == repartition_type).mapped('tag_ids')

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
        """ Returns all information required to apply taxes (in self + their children in case of a tax group).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

            'handle_price_include' is used when we need to ignore all tax included in price. If False, it means the
            amount passed to this method will be considered as the base of all computations.

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'total_void'    : 0.0,    # Total with those taxes, that don't have an account set
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }],
        } """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        # 1) Flatten the taxes.
        taxes = self.flatten_taxes_hierarchy()

        # 2) Avoid mixing taxes having price_include=False && include_base_amount=True
        # with taxes having price_include=True. This use case is not supported as the
        # computation of the total_excluded would be impossible.
        include_base_amount_price_include = False # price_include=True && include_base_amount=True
        include_base_amount_price_exclude = False # price_include=False && include_base_amount=True
        allow_not_affected_tax = False
        for tax in taxes:
            if tax.price_include and tax.include_base_amount:
                include_base_amount_price_include = True
            elif not tax.price_include and tax.include_base_amount:
                include_base_amount_price_exclude = True
            if tax.include_base_amount and tax.is_affected_former_tax:
                allow_not_affected_tax = True
            elif tax.include_base_amount and not tax.is_affected_former_tax:
                if not allow_not_affected_tax:
                    raise UserError(_("Unable to use not affected by former taxes option if not following a tax affecting the base amount."))
            else:
                allow_not_affected_tax = False

        if include_base_amount_price_include and include_base_amount_price_exclude:
            raise UserError(_('Unable to mix any taxes being price included with taxes affecting the base amount but not included in price.'))

        # 3) Deal with the rounding methods
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
        prec = currency.decimal_places

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec += 5

        # 4) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        #     tax  |  base  |  amount  |
        # /\ ----------------------------
        # || tax_1 |  XXXX  |          | <- we are looking for that, it's the total_excluded
        # || tax_2 |   ..   |          |
        # || tax_3 |   ..   |          |
        # ||  ...  |   ..   |    ..    |
        #    ----------------------------
        def recompute_base(base_amount, fixed_amount, percent_amount, division_amount):
            # Recompute the new base amount based on included fixed/percent amounts and the current base amount.
            # Example:
            #  tax  |  amount  |   type   |  price_include  |
            # -----------------------------------------------
            # tax_1 |   10%    | percent  |  t
            # tax_2 |   15     |   fix    |  t
            # tax_3 |   20%    | percent  |  t
            # tax_4 |   10%    | division |  t
            # -----------------------------------------------

            # if base_amount = 145, the new base is computed as:
            # (145 - 15) / (1.0 + 30%) * 90% = 130 / 1.3 * 90% = 90
            return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100

        # The first/last base must absolutely be rounded to work in round globally.
        # Indeed, the sum of all taxes ('taxes' key in the result dictionary) must be strictly equals to
        # 'price_included' - 'price_excluded' whatever the rounding method.
        #
        # Example using the global rounding without any decimals:
        # Suppose two invoice lines: 27000 and 10920, both having a 19% price included tax.
        #
        #                   Line 1                      Line 2
        # -----------------------------------------------------------------------
        # total_included:   27000                       10920
        # tax:              27000 / 1.19 = 4310.924     10920 / 1.19 = 1743.529
        # total_excluded:   22689.076                   9176.471
        #
        # If the rounding of the total_excluded isn't made at the end, it could lead to some rounding issues
        # when summing the tax amounts, e.g. on invoices.
        # In that case:
        #  - amount_untaxed will be 22689 + 9176 = 31865
        #  - amount_tax will be 4310.924 + 1743.529 = 6054.453 ~ 6054
        #  - amount_total will be 31865 + 6054 = 37919 != 37920 = 27000 + 10920
        #
        # By performing a rounding at the end to compute the price_excluded amount, the amount_tax will be strictly
        # equals to 'price_included' - 'price_excluded' after rounding and then:
        #   Line 1: sum(taxes) = 27000 - 22689 = 4311
        #   Line 2: sum(taxes) = 10920 - 2176 = 8744
        #   amount_tax = 4311 + 8744 = 13055
        #   amount_total = 31865 + 13055 = 37920
        base = currency.round(price_unit * quantity)

        # For the computation of move lines, we could have a negative base value.
        # In this case, compute all with positive values and negate them at the end.
        sign = 1
        if base < 0:
            base = -base
            sign = -1

        if is_refund:
            tax_rep_field = 'refund_repartition_line_ids'
        else:
            tax_rep_field = 'invoice_repartition_line_ids'

        collected_tax_vals_list = []

        # Keep track of the accumulated included fixed/percent amount.
        incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
        collected_subsequent_taxes = self.env['account.tax']
        collected_not_affected_subsequent_taxes = self.env['account.tax']
        first_encountered_price_include_tax = True
        is_in_include_base_amount_group = False
        for i, tax in enumerate(reversed(taxes)):

            # Collect data about the current tax to avoid performing multiple times the same things and then, causing
            # some inconsistencies.
            collected_tax_vals = {
                'tax_repartition_lines': tax[tax_rep_field].filtered(lambda x: x.repartition_type == 'tax'),
                'price_include': tax.price_include or self._context.get('force_price_include'),
            }
            collected_tax_vals['factor'] = sum(collected_tax_vals['tax_repartition_lines'].mapped('factor'))

            # Without 'handle_price_include', all taxes must be considered as not included in price in the first
            # reversal descent only.
            price_include = collected_tax_vals['price_include'] and handle_price_include

            # Compute manually the amount of taxes that must give zero as result.
            # This is done like this to avoid an amount != 0 is set to avoid rounding issues when such tax is the last
            # before the next computation base.
            if not tax.amount and tax.amount_type in ('percent', 'division', 'fixed'):
                collected_tax_vals['tax_amount'] = collected_tax_vals['factorized_tax_amount'] = 0.0

            if tax.include_base_amount and not is_in_include_base_amount_group:
                # Enter one of multiple taxes having include_base_amount=True but some could have
                # is_affected_former_tax=False.
                is_in_include_base_amount_group = True

                # At this point, we have a new computation base. Keep track of them in order to fix rounding issues
                # later.
                if collected_tax_vals_list:
                    base = round(recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount), prec)
                    incl_fixed_amount = incl_percent_amount = incl_division_amount = 0

                    if price_include:
                        collected_tax_vals_list[-1]['base'] = base

            if price_include:
                factorized_tax_amount = tax.amount * collected_tax_vals['factor']
                if tax.amount_type == 'percent':
                    incl_percent_amount += factorized_tax_amount
                elif tax.amount_type == 'division':
                    incl_division_amount += factorized_tax_amount
                elif tax.amount_type == 'fixed':
                    incl_fixed_amount += quantity * factorized_tax_amount
                else: # tax.amount_type == other (python)
                    collected_tax_vals['tax_amount'] = tax._compute_amount(base, sign * price_unit, quantity, product, partner)
                    factorized_tax_amount = round(collected_tax_vals['tax_amount'] * collected_tax_vals['factor'], prec)
                    collected_tax_vals['factorized_tax_amount'] = factorized_tax_amount
                    incl_fixed_amount += factorized_tax_amount

                if first_encountered_price_include_tax and 'tax_amount' not in collected_tax_vals:
                    collected_tax_vals['initial_base'] = base
                    first_encountered_price_include_tax = False

            if tax.include_base_amount:

                if tax.is_affected_former_tax:
                    # Exit the group of taxes affecting the base of subsequent ones.
                    is_in_include_base_amount_group = False
                    base = round(recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount), prec)
                    incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
                    if price_include:
                        collected_tax_vals['base'] = base
                    collected_tax_vals['subsequent_taxes'] = collected_subsequent_taxes
                    collected_tax_vals['subsequent_tags'] = collected_subsequent_taxes.get_tax_tags(is_refund, 'base')
                    collected_subsequent_taxes += collected_not_affected_subsequent_taxes
                    collected_not_affected_subsequent_taxes = self.env['account.tax']
                else:
                    collected_not_affected_subsequent_taxes |= tax

            if tax.is_affected_former_tax:
                collected_subsequent_taxes |= tax

            # The first base (total_excluded) must always be rounded using the decimal precision of the currency
            # even with round_globally.
            if i == len(taxes) - 1:
                base = currency.round(recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount))
                collected_tax_vals['base'] = base
                incl_fixed_amount = incl_percent_amount = incl_division_amount = 0

            collected_tax_vals_list.append(collected_tax_vals)

        collected_tax_vals_list = list(reversed(collected_tax_vals_list))

        # 5) Iterate the taxes in the sequence order to compute missing tax amounts.
        # Start the computation of accumulated amounts at the total_excluded value.
        total_included = total_void = total_excluded = base

        taxes_vals = []
        cumulated_tax_included_amount = 0
        cumutated_base_amount = 0
        is_in_include_base_amount_group = False
        for i, tax in enumerate(taxes.with_context(force_price_include=False)):
            collected_tax_vals = collected_tax_vals_list[i]

            if tax.include_base_amount and not collected_tax_vals['price_include'] and not is_in_include_base_amount_group:
                is_in_include_base_amount_group = True
            if not tax.include_base_amount and is_in_include_base_amount_group:
                is_in_include_base_amount_group = False
                base += cumutated_base_amount
                cumutated_base_amount = 0

            if 'base' in collected_tax_vals:
                base = collected_tax_vals['base']
                cumulated_tax_included_amount = 0
            else:
                collected_tax_vals['base'] = base

            if 'tax_amount' not in collected_tax_vals:
                if 'initial_base' in collected_tax_vals:
                    next_base = collected_tax_vals['initial_base']
                elif collected_tax_vals['price_include'] and i + 1 < len(collected_tax_vals_list) and 'base' in collected_tax_vals_list[i + 1]:
                    next_base = collected_tax_vals_list[i + 1]['base']
                else:
                    next_base = None

                if next_base is None:
                    tax_amount = tax._compute_amount(collected_tax_vals['base'], sign * price_unit, quantity, product, partner)
                    collected_tax_vals['tax_amount'] = tax_amount
                    collected_tax_vals['factorized_tax_amount'] = round(tax_amount * collected_tax_vals['factor'], prec)
                else:
                    collected_tax_vals['factorized_tax_amount'] = next_base - collected_tax_vals['base'] - cumulated_tax_included_amount
                    collected_tax_vals['tax_amount'] = collected_tax_vals['factorized_tax_amount'] / collected_tax_vals['factor']

            if collected_tax_vals['price_include']:
                cumulated_tax_included_amount += collected_tax_vals['factorized_tax_amount']
            elif tax.include_base_amount:
                cumutated_base_amount += collected_tax_vals['factorized_tax_amount']

            # Manage the repartition lines.

            repartition_line_amounts = [round(collected_tax_vals['tax_amount'] * line.factor, prec)
                                        for line in collected_tax_vals['tax_repartition_lines']]
            total_rounding_error = round(collected_tax_vals['factorized_tax_amount'] - sum(repartition_line_amounts), prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = round(total_rounding_error / nber_rounding_steps, prec) if nber_rounding_steps else 0.0

            for repartition_line, line_amount in zip(collected_tax_vals['tax_repartition_lines'], repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                account = tax.cash_basis_transition_account_id if tax.tax_exigibility == 'on_payment' else repartition_line.account_id
                subsequent_tags = collected_tax_vals.get('subsequent_tags', self.env['account.account.tag'])
                subsequent_taxes = collected_tax_vals.get('subsequent_taxes', self.env['account.tax'])

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': round(sign * collected_tax_vals['base'], prec),
                    'sequence': tax.sequence,
                    'account_id': account.id,
                    'analytic': tax.analytic,
                    'price_include': collected_tax_vals['price_include'],
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'tag_ids': (repartition_line.tag_ids + subsequent_tags).ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            total_included += collected_tax_vals['factorized_tax_amount']

        return {
            'base_tags': taxes.mapped(tax_rep_field).filtered(lambda x: x.repartition_type == 'base').mapped('tag_ids').ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * currency.round(total_void),
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

    factor_percent = fields.Float(string="%", required=True, help="Factor to apply on the account move lines generated from this distribution line, in percents")
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the account move lines generated from this distribution line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('internal_type', 'not in', ('receivable', 'payable'))]",
        check_company=True,
        help="Account on which to post the tax amount")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True)
    invoice_tax_id = fields.Many2one(comodel_name='account.tax',
        check_company=True,
        help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax',
        check_company=True,
        help="The tax set to apply this distribution on refund invoices. Mutually exclusive with invoice_tax_id")
    tax_id = fields.Many2one(comodel_name='account.tax', compute='_compute_tax_id')
    tax_fiscal_country_id = fields.Many2one(string="Fiscal Country", comodel_name='res.country', related='company_id.account_tax_fiscal_country_id', help="Technical field used to restrict tags domain in form view.")
    company_id = fields.Many2one(string="Company", comodel_name='res.company', compute="_compute_company", store=True, help="The company this distribution line belongs to.")
    sequence = fields.Integer(string="Sequence", default=1, help="The order in which display and match distribution lines. For refunds to work properly, invoice distribution lines should be arranged in the same order as the credit note distribution lines they correspond to.")
    use_in_tax_closing = fields.Boolean(string="Tax Closing Entry")

    @api.onchange('account_id')
    def _on_change_account_id(self):
        if not self.account_id:
            self.use_in_tax_closing = False
        else:
            self.use_in_tax_closing = not(self.account_id.internal_group == 'income' or self.account_id.internal_group == 'expense')

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

    @api.onchange('repartition_type')
    def _onchange_repartition_type(self):
        if self.repartition_type == 'base':
            self.account_id = None
