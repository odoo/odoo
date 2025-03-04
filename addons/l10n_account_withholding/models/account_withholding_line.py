# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from itertools import chain

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.osv import expression
from odoo.tools.misc import frozendict


class AccountWithholdingLine(models.AbstractModel):
    """ Abstract model to hold as much as possible the logic of a withholding line that can be found on the payment/register payment wizard. """
    _name = 'account.withholding.line'
    _inherit = "analytic.mixin"
    _description = 'withholding line'
    _check_company_auto = True

    # ------------------
    # Fields declaration
    # ------------------

    name = fields.Char(string='Sequence Number')
    type_tax_use = fields.Char(compute='_compute_type_tax_use')
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        required=True,
        domain="[('type_tax_use', '=', type_tax_use), ('is_withholding_tax_on_payment', '=', True)]"
    )
    withholding_sequence_id = fields.Many2one(related='tax_id.withholding_sequence_id')
    original_base_amount = fields.Monetary(required=True)
    base_amount = fields.Monetary(
        compute='_compute_base_amount',
        precompute=True,
        required=True,
        readonly=False,
        store=True,
    )
    amount = fields.Monetary(
        string='Withheld Amount',
        compute='_compute_amount',
    )
    custom_user_amount = fields.Monetary()
    custom_user_currency_id = fields.Many2one(comodel_name='res.currency')
    # Fields related to the comodel, computed in child models.
    company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_company_id',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        compute='_compute_account_id',
        store=True,
        readonly=False,
        required=True,
    )
    comodel_original_amount = fields.Monetary(compute='_compute_comodel_original_amount')
    comodel_amount = fields.Monetary(compute='_compute_comodel_amount')
    comodel_date = fields.Date(compute='_compute_comodel_date')
    comodel_payment_type = fields.Selection(
        selection=[
            ('outbound', 'Send Money'),
            ('inbound', 'Receive Money'),
        ],
        compute='_compute_comodel_payment_type',
    )
    # todo
    """
    Remove all logic computing the tax amount here, and we keep it on the wizard and payment.
    """

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        AccountTax = self.env['account.tax']
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                base_line = line._prepare_base_line_for_taxes_computation()
                AccountTax._add_tax_details_in_base_line(base_line, self.company_id)
                AccountTax._round_base_lines_tax_details([base_line], self.company_id)
                tax_details = base_line['tax_details']
                line.amount = sum(tax_data['tax_amount_currency'] for tax_data in tax_details['taxes_data'])

    @api.depends('original_base_amount')
    def _compute_base_amount(self):
        """ The base_amount is manually editable, but will also be dynamically computed by default.
        If the amount of the payment/register payment linked to the line is edited, the base amount will also be re-computed.
        """
        for line in self:
            if not line.custom_user_amount:
                line.base_amount = line._get_default_base_amount()
            else:
                line.base_amount = line.custom_user_amount

    @api.depends('company_id')
    def _compute_account_id(self):
        for line in self:
            line.account_id = line.account_id or line.company_id.withholding_tax_base_account_id

    # The following computes are related to the comodel (payment or register payment wizard) and are needed for various computations.

    def _compute_type_tax_use(self):
        raise NotImplementedError()

    def _compute_company_id(self):
        raise NotImplementedError()

    def _compute_currency_id(self):
        raise NotImplementedError()

    def _compute_comodel_original_amount(self):
        raise NotImplementedError()

    def _compute_comodel_amount(self):
        raise NotImplementedError()

    def _compute_comodel_date(self):
        raise NotImplementedError()

    def _compute_comodel_payment_type(self):
        raise NotImplementedError()

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.constrains('base_amount')
    def _constrains_base_amount(self):
        """ It wouldn't make sense to register a withholding tax with no base amount. """
        for line in self:
            if line.currency_id.compare_amounts(line.base_amount, 0) <= 0:
                raise UserError(line.env._("The base amount of a withholding tax line must above 0."))

    @api.onchange('base_amount')
    def _onchange_base_amount(self):
        """ Register if the user has input a custom amount; if so we don't want to recompute it automatically.
        We still want to handle currency conversion, though.
        """
        if not self.currency_id:
            return

        is_custom_user_amount = self.base_amount != self._get_default_base_amount()
        if is_custom_user_amount:
            self.custom_user_amount = self.base_amount
            self.custom_user_currency_id = self.currency_id
        else:
            self.custom_user_amount = None
            self.custom_user_currency_id = None

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model_create_multi
    def create(self, vals_list):
        # EXTEND to populate the original base amount with the amount value at creation.
        for vals in vals_list:
            if 'original_base_amount' not in vals and 'base_amount' in vals:
                vals['original_base_amount'] = vals['base_amount']

        return super().create(vals_list)

    # ----------------
    # Business methods
    # ----------------

    def _get_default_base_amount(self):
        """ Helper which retrieves the original base amount, in the comodel currency.
        It takes into account the ratio calculated based on the payment original and current amount.
        """
        self.ensure_one()
        if not self.comodel_original_amount:
            ratio = 1
        else:
            # We convert comodel_original_amount to the comodel currency, as comodel_amount is in this currency.
            cc_comodel_original_amount = self.company_id.currency_id._convert(
                self.comodel_original_amount,
                self.currency_id,
                self.company_id,
                self.comodel_date,
            )
            ratio = self.comodel_amount / cc_comodel_original_amount

        cc_original_base_amount = self.company_id.currency_id._convert(
            self.original_base_amount,
            self.currency_id,
            self.company_id,
            self.comodel_date,
        )
        return cc_original_base_amount * ratio

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()
        company = self.company_id
        currency = self.currency_id
        conversion_date = self.comodel_date
        conversion_rate = self.env['res.currency']._get_conversion_rate(company.currency_id, currency, company, conversion_date)
        payment_type = self.comodel_payment_type
        sign = 1 if payment_type == 'inbound' else -1
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.tax_id,
            price_unit=self.base_amount,
            quantity=1.0,
            special_mode='total_included',
            rate=conversion_rate,
            sign=sign,
            account_id=self.account_id,
            calculate_withholding_taxes=True,
        )

    def _prepare_withholding_line_vals(self):
        """ Prepare and return a list of values that will be used to create the journal items for the withholding lines.

        For an invoice for 1000 with 10% withholding tax:
        Outstanding:  900.0
        Receivable:           1000.0
        Tax withheld: 10.0
        WHT base:     1000.0
        WHT base:             1000.0

        :return: A list of dictionaries, each one being a journal item to be created.
        """
        if not self:
            return []

        company = self.company_id
        AccountTax = self.env['account.tax']

        # Convert them to base lines to compute the taxes.
        base_lines = []
        for line in self:
            if not line.name:
                line.name = line.tax_id.withholding_sequence_id.next_by_id()

            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            base_lines.append(base_line)
        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, company)
        tax_results = AccountTax._prepare_tax_lines(base_lines, company)

        # Add the tax lines.
        aml_create_values_list = []
        for tax_line_vals in tax_results['tax_lines_to_add']:
            aml_create_values_list.append({
                **tax_line_vals,
                'name': _("WH Tax: %(name)s", name=tax_line_vals['name']),
            })

        # Aggregate the base lines.
        aggregated_base_lines = defaultdict(list)
        for base_line, to_update in tax_results['base_lines_to_update']:
            grouping_key = frozendict({
                'tax_tag_ids': to_update['tax_tag_ids'],
                'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                'account_id': base_line['account_id'].id,
                'currency_id': base_line['currency_id'].id,
                'base_amount': base_line['record'].base_amount,
                'analytic_distribution': base_line['analytic_distribution'],
            })
            aggregated_base_lines[grouping_key].append({
                'name': base_line['record'].name,
                'currency_id': base_line['currency_id'].id,
                'account_id': base_line['account_id'].id,
                'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                **to_update,

                # Hack the returned 'amount_currency' to avoid a rounding issue.
                # Since the base lines are added twice just for the record, it won't unbalanced the accounting entry.
                'amount_currency': base_line['record'].base_amount * base_line['sign'],
            })

        # Add the base lines.
        for sub_aml_create_values_list in aggregated_base_lines.values():
            amount_currency = sum(base_line['amount_currency'] for base_line in sub_aml_create_values_list)
            balance = sum(base_line['balance'] for base_line in sub_aml_create_values_list)
            aml_create_values_list.append({
                **sub_aml_create_values_list[0],
                'name': _('WH Base: %(names)s', names=', '.join(base_line['name'] for base_line in sub_aml_create_values_list)),
                'amount_currency': amount_currency,
                'balance': balance,
            })
            aml_create_values_list.append({
                **sub_aml_create_values_list[0],
                'name': _('WH Base Counterpart: %(names)s', names=', '.join(base_line['name'] for base_line in sub_aml_create_values_list)),
                'tax_ids': [],
                'tax_tag_ids': [],
                'amount_currency': -amount_currency,
                'balance': -balance,
            })

        return aml_create_values_list

    @api.model
    def _get_withholding_tax_domain(self, company, payment_type):
        """ Construct and return a domain that will filter withholding taxes available for this company and payment type. """
        company = company
        filter_domain = models.check_company_domain_parent_of(self, company)
        payment_type = 'purchase' if payment_type == 'outbound' else 'sale'
        return expression.AND([filter_domain, [('type_tax_use', '=', payment_type), ('is_withholding_tax_on_payment', '=', True)]])

    def _get_grouping_key(self):
        """ Helper returning the grouping key for this line; should match what is done in _compute_withholding_lines on the wizard. """
        self.ensure_one()
        return frozendict({
            'analytic_distribution': self.analytic_distribution,
            'account': self.account_id,
            'tax': self.tax_id,
            'skip': False,
        })
