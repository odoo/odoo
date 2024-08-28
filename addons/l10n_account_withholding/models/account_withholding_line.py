# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from itertools import chain

from odoo import api, Command, fields, models
from odoo.exceptions import UserError, RedirectWarning
from odoo.osv import expression


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

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        """ The amount displayed on the line is the sum amount of all repartition lines.
        The amount will be split according to the repartition lines when the payment is synced with the journal entry.
        """
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = sum(tax['amount'] for tax in line._get_withholding_tax_values())

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

    def _get_withholding_tax_values(self):
        """ Helper that uses compute_all in order to return the tax details. """
        self.ensure_one()
        tax_values = self.tax_id.compute_all(price_unit=self.base_amount, currency=self.currency_id)
        return [{
            'amount': tax['amount'],
            'account': tax['account_id'],
            'tax_repartition_line': tax['tax_repartition_line_id'],
            'tax_name': tax['name'],
            'tax_base_amount': tax['base'],
            'tag_ids': tax['tag_ids'],
        } for tax in tax_values['taxes']]

    def _get_withholding_tax_base_tag_ids(self):
        """ Helper which returns the tax tags applied to the base repartition line for the withholding lines in self. """
        tag_ids = set()
        for line in self:
            tax_values = line.tax_id.compute_all(price_unit=line.base_amount, currency=line.currency_id)
            tag_ids.update(tax_values['base_tags'])
        return tag_ids

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

    def _prepare_withholding_line_vals_data(self):
        """ Helper to prepare and format the date required by _prepare_withholding_line_vals. """
        # Some data is going to be the same for all withholding lines of a same record.
        # As this is expected to be called in this case, these values should always be the same.
        tax_base_account_id = self[0].company_id.withholding_tax_base_account_id.id
        if not tax_base_account_id:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(
                self.env._('To register withholding taxes, the "Withholding Tax Base Account" must be set in the settings.'),
                action.id,
                self.env._('Accounting Settings')
            )

        data = {
            'currency_id': self[0].currency_id.id,
            'date': self[0].comodel_date,
            'company_id': self[0].company_id.id,
            'payment_type': self[0].comodel_payment_type,
            'tax_base_account_id': tax_base_account_id,
            'withholding_line_vals': [],
        }
        for line in self:
            withholding_tax_values = line._get_withholding_tax_values()
            for tax in withholding_tax_values:
                tax_account = tax['account']
                if not tax_account:
                    raise UserError(self.env._('Please define a tax account on the distribution of the tax %(tax_name)s', tax_name=tax['tax_name']))

            if not line.name:
                line.name = line.tax_id.withholding_sequence_id.next_by_id()

            data['withholding_line_vals'].append({
                'withholding_tax_values': withholding_tax_values,
                'name': line.name,
                'base_amount': line.base_amount,
                'base_tag_ids': line._get_withholding_tax_base_tag_ids(),
                'tax_id': line.tax_id.id,
                'analytic_distribution': line.analytic_distribution,
            })
        return data

    def _prepare_withholding_line_vals(self):
        """ Prepare and return a list of dicts containing the data required to generate the journal items for the withholding lines. """
        if not self:
            return []

        withholding_line_vals_data = self._prepare_withholding_line_vals_data()

        sign = 1 if withholding_line_vals_data['payment_type'] == 'inbound' else -1
        payment_currency = self.env['res.currency'].browse(withholding_line_vals_data['currency_id'])
        payment_company = self.env['res.company'].browse(withholding_line_vals_data['company_id'])
        payment_date = withholding_line_vals_data['date']

        withholding_line_vals = []
        dict_group = defaultdict(list)
        for withholding_line_val in withholding_line_vals_data['withholding_line_vals']:
            # We need to support using multiple tax repartition lines, but in the wizard one tax = one line.
            # So, we'll only split the result here. If the amount of the line has been set manually, _get_withholding_tax_values already returns the tax details for that amount.
            for tax in withholding_line_val['withholding_tax_values']:
                withholding_line_vals.append({
                    'currency_id': payment_currency.id,
                    'name': withholding_line_val['name'],
                    'account_id': tax['account'],
                    'amount_currency': sign * tax['amount'],
                    'balance': sign * payment_currency._convert(tax['amount'], payment_company.currency_id, payment_company, payment_date),
                    'tax_base_amount': tax['tax_base_amount'],
                    'tax_repartition_line_id': tax['tax_repartition_line'],
                    'tax_tag_ids': [Command.set(tax['tag_ids'])],
                    'analytic_distribution': withholding_line_val['analytic_distribution'],
                })
            # We also need tax base lines for reporting.
            # Group the withholding lines by their base amount and base tags.
            dict_group[(withholding_line_val['base_amount'], self.env['account.account.tag'].browse(withholding_line_val['base_tag_ids']))].append(withholding_line_val)

        base_lines_to_create = []
        # This looping loop aim is to optimize the amount of account.move.line being created by this flow by grouping them.
        for (group_base_amount, group_tags), withholding_lines_val in dict_group.items():
            # This base amount grouped above need to be multiplied in order to correctly affect the tax tags
            group_base_amount *= len(withholding_lines_val)

            # If we have a line in our list which has a base amount matching the one of the current group and which also
            # doesn't have any of the tags inside, we can merge this group with that one to save records.
            for i in range(len(base_lines_to_create)):
                ((base_amount, tags), lines) = base_lines_to_create[i]
                if (base_amount == group_base_amount) and not (tags & group_tags):
                    base_lines_to_create[i] = ((base_amount, tags + group_tags), lines + withholding_lines_val)
                    break
            else:
                base_lines_to_create.append(((group_base_amount, group_tags), withholding_lines_val))

        balance_sum = amount_currency_sum = 0
        for (base_amount, tags), withholding_lines in base_lines_to_create:
            withholding_numbers = ', '.join([line['name'] for line in withholding_lines])
            base_amount = sign * base_amount
            cc_base_amount = payment_currency._convert(base_amount, payment_company.currency_id, payment_company, payment_date)
            balance_sum += cc_base_amount
            amount_currency_sum += base_amount
            withholding_line_vals.append({
                'currency_id': payment_currency.id,
                'name': self.env._('WH Base: %(withholding_numbers)s', withholding_numbers=withholding_numbers),
                'tax_ids': [Command.set([line['tax_id'] for line in withholding_lines])],
                'account_id': withholding_line_vals_data['tax_base_account_id'],
                'balance': cc_base_amount,
                'amount_currency': base_amount,
                'tax_tag_ids': [Command.set(list(set(chain.from_iterable([line['base_tag_ids'] for line in withholding_lines]))))],
            })

        # counterpart line vals
        withholding_line_vals.append({
            'currency_id': payment_currency.id,
            'name': self.env._('WH Base Counterpart'),
            'account_id': withholding_line_vals_data['tax_base_account_id'],
            'balance': -balance_sum,
            'amount_currency': -amount_currency_sum,
        })

        return withholding_line_vals

    @api.model
    def _get_withholding_tax_domain(self, company, payment_type):
        """ Construct and return a domain that will filter withholding taxes available for this company and payment type. """
        company = company
        filter_domain = models.check_company_domain_parent_of(self, company)
        payment_type = 'purchase' if payment_type == 'outbound' else 'sale'
        return expression.AND([filter_domain, [('type_tax_use', '=', payment_type), ('is_withholding_tax_on_payment', '=', True)]])
