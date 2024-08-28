# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, RedirectWarning
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_display_withholding = fields.Boolean(compute='_compute_l10n_account_withholding_display_withholding')
    l10n_account_withholding_withhold_tax = fields.Boolean(
        string='Withhold Tax Amounts',
        compute='_compute_from_lines',
        store=True,
        readonly=False,
    )
    l10n_account_withholding_line_ids = fields.One2many(
        string="Withholding Lines",
        comodel_name='account.payment.withholding.line',
        inverse_name='payment_register_id',
        compute='_compute_from_lines',
        store=True,
        readonly=False,
    )
    l10n_account_withholding_hide_number_col = fields.Boolean(compute='_compute_l10n_account_withholding_hide_number_col')
    l10n_account_withholding_net_amount = fields.Monetary(
        string='Net Amount',
        help="Net amount after deducting the withholding lines",
        compute='_compute_l10n_account_withholding_net_amount',
    )
    # We need to define the outstanding account of the payment in order for it to have the proper journal entry.
    # To that end, we'll have this field required if we have a withholding tax impacting the payment and we don't have a payment account set on the payment method.
    l10n_account_withholding_journal_default_account_id = fields.Many2one(
        related='journal_id.default_account_id'
    )
    l10n_account_withholding_outstanding_account = fields.Many2one(
        comodel_name='account.account',
        string="Outstanding Account",
        copy=False,
        domain="[('deprecated', '=', False), '|', ('account_type', 'in', ('asset_current', 'liability_current')), ('id', '=', l10n_account_withholding_journal_default_account_id)]",
        check_company=True,
        compute="_compute_l10n_account_withholding_outstanding_account",
        store=True,
        readonly=False,
    )
    l10n_account_withholding_payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    l10n_account_withholding_payment_invoice_amount_total = fields.Monetary(
        compute="_compute_from_lines",
        store=True,
        readonly=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------d

    @api.depends('l10n_account_withholding_line_ids.amount', 'amount')
    def _compute_l10n_account_withholding_net_amount(self):
        for wizard in self:
            wizard.l10n_account_withholding_net_amount = wizard.amount - sum(wizard.l10n_account_withholding_line_ids.mapped('amount'))

    @api.depends('l10n_account_withholding_line_ids.tax_id')
    def _compute_l10n_account_withholding_hide_number_col(self):
        for wizard in self:
            wizard.l10n_account_withholding_hide_number_col = (
                    wizard.l10n_account_withholding_line_ids and
                    all(line.withholding_sequence_id for line in wizard.l10n_account_withholding_line_ids)
            )

    @api.depends('l10n_account_withholding_payment_account_id')
    def _compute_l10n_account_withholding_outstanding_account(self):
        """ We propose a default account by getting one from the latest payment which:
            - Has the same payment method line id (and thus indirectly the same journal, and thus the same company)
            - That payment method has no payment_account_id
            - Yet the payment has an outstanding_account_id
         """
        for wizard in self:
            latest_payment = self.env['account.payment'].search_read(
                domain=[
                    ('payment_method_line_id', '=', wizard.payment_method_line_id.id),
                    ('payment_method_line_id.payment_account_id', '=', False),
                    ('outstanding_account_id', '!=', False),
                ],
                fields=['outstanding_account_id'],
                limit=1,
                order='id desc'
            )
            if wizard.l10n_account_withholding_payment_account_id or not latest_payment:
                wizard.l10n_account_withholding_outstanding_account = False  # we'll use the payment method one.
            else:
                wizard.l10n_account_withholding_outstanding_account = latest_payment[0]['outstanding_account_id'][0]

    @api.depends('company_id', 'can_edit_wizard', 'can_group_payments', 'group_payment')
    def _compute_l10n_account_withholding_display_withholding(self):
        """ We want to hide the withholding tax checkbox in three cases:
         - If there are now withholding taxes in the company;
         - If we are registering payments from multiple entries, where we would end up generating multiple payments;
         - In argentina
        """
        for wizard in self:
            available_withholding_taxes = self.env['account.tax'].search(wizard._get_withholding_tax_domain())
            will_create_multiple_entry = not wizard.can_edit_wizard or (wizard.can_group_payments and not wizard.group_payment)
            wizard.l10n_account_withholding_display_withholding = available_withholding_taxes and not will_create_multiple_entry and not wizard.country_code == 'AR'

    @api.depends('line_ids')
    def _compute_from_lines(self):
        """
        Extended in order to pre-populate the withholding lines based on the taxes set on the products of the invoice.

        Products can have withholding taxes assigned to them.
        These will not appear on the invoice, but are intended to be used here to pre-populate the withholding tax lines.
        We will make one line per withholding tax, and pre-set the base amount as the sum of the lines with a product having this tax set.
        """
        # EXTEND account
        super()._compute_from_lines()
        for wizard in self:
            if wizard.country_code == 'AR':
                wizard.l10n_account_withholding_line_ids = False
                continue

            withholding_line_creation_vals = []
            invoice_amount_total = 0.0
            if wizard.can_edit_wizard:
                withholding_line_amounts = defaultdict(int)
                batch_result = wizard.batches[0]
                for move in batch_result['lines'].move_id:
                    invoice_amount_total += move.amount_total  # We take the amount in company currency, which will be easier to convert when/if the wizard currency changes.
                    for line in move.invoice_line_ids:
                        taxes = line.product_id.taxes_id if move.is_sale_document(include_receipts=True) else line.product_id.supplier_taxes_id
                        withholding_taxes = taxes.filtered_domain(wizard._get_withholding_tax_domain(move.company_id))
                        for withholding_tax in withholding_taxes:
                            # Check if the move has a fiscal position and apply if needed.
                            if move.fiscal_position_id:
                                withholding_tax = move.fiscal_position_id.map_tax(withholding_tax)
                            withholding_line_amounts[withholding_tax] += abs(line.balance)  # The base amount is always a positive amount

                for withholding_tax, withholding_line_amount in withholding_line_amounts.items():
                    withholding_line_creation_vals.append(Command.create({
                        'tax_id': withholding_tax.id,
                        'full_base_amount': withholding_line_amount,
                    }))
            wizard.l10n_account_withholding_withhold_tax = bool(withholding_line_creation_vals)
            wizard.l10n_account_withholding_line_ids = withholding_line_creation_vals
            wizard.l10n_account_withholding_payment_invoice_amount_total = invoice_amount_total

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        # EXTEND account
        super()._onchange_currency_id()
        # Done here as the onchange does not trigger on the line.
        for line in self.l10n_account_withholding_line_ids:
            if line.custom_user_amount:
                # We convert from the custom currency id of the wizard to the new currency id.
                line.custom_user_amount = line.base_amount = line.custom_user_currency_id._convert(
                    from_amount=line.custom_user_amount,
                    to_currency=line.currency_id,
                    date=line.payment_date,
                    company=line.company_id,
                )
                # As we handle this on the wizard itself, we can't rely on the onchange to update this.
                line.custom_user_currency_id = line.currency_id

    # ----------------
    # Business methods
    # ----------------

    def _create_payment_vals_from_wizard(self, batch_result):
        # EXTEND account
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        if not self.l10n_account_withholding_line_ids or not self.l10n_account_withholding_withhold_tax:
            return payment_vals  # Nothing to do if we are not working with withholding taxes.

        # Get the account set on the company; raise an error if not set.
        tax_base_account = self.company_id.l10n_account_withholding_tax_base_account_id.id
        if not tax_base_account:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(
                _('To register withholding taxes, the "Withholding Tax Base Account" must be set in the settings.'),
                action.id,
                _('Accounting Settings')
            )
        # The payment amount is the base amount set in the wizard, minus the sum of the withholding line amounts.
        payment_vals['amount'] = self.l10n_account_withholding_net_amount
        # Ensure that we get a journal entry
        if self.l10n_account_withholding_outstanding_account:
            payment_vals['outstanding_account_id'] = self.l10n_account_withholding_outstanding_account.id
        # We need to process the withholding here as the records are transient, and it won't be done by the payment.
        # /!\ including currency conversion if needed.
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            self.currency_id,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date,
        )

        sign = 1 if self.payment_type == 'inbound' else -1

        # The first step is to add withholding lines.
        for withholding_line in self.l10n_account_withholding_line_ids:
            # For each withholding line, we need to create a write_off_line with the values of the tax.
            withholding_tax_values = withholding_line._get_withholding_tax_values()

            if not withholding_line.name:
                if withholding_line.tax_id.l10n_account_withholding_sequence_id:
                    withholding_line.name = withholding_line.tax_id.l10n_account_withholding_sequence_id.next_by_id()
                else:
                    raise UserError(_('Please enter the withholding number for the tax %(tax_name)s', tax_name=withholding_tax_values['tax_name']))

            tax_account = withholding_tax_values['account']
            if not tax_account:
                raise UserError(_('Please define a tax account on the distribution of the tax %(tax_name)s', tax_name=withholding_tax_values['tax_name']))

            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,
                'name': f'WH Tax: {withholding_line.name}',
                'account_id': tax_account,
                'amount_currency': sign * withholding_line.amount,
                'balance': sign * self.company_currency_id.round(withholding_line.amount * conversion_rate),
                'tax_base_amount': withholding_tax_values['tax_base_amount'],
                'tax_repartition_line_id': withholding_tax_values['tax_repartition_line'],
                'tax_tag_ids': [Command.set(withholding_tax_values['tag_ids'])],
            })

        # We also need tax base lines for reporting. We simply create one per unique base amount.
        balance_sum = amount_currency_sum = 0
        for base_amount, withholding_lines in self.l10n_account_withholding_line_ids.grouped('base_amount').items():
            withholding_numbers = ','.join(withholding_lines.mapped('name'))
            base_amount = sign * base_amount
            cc_base_amount = self.company_currency_id.round(base_amount * conversion_rate)
            # The aim is to get one base line with the correct amount, and a counterpart that cancels it.
            balance_sum += cc_base_amount
            amount_currency_sum += base_amount
            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,
                'name': f'WH Base: {withholding_numbers}',
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
                'account_id': tax_base_account,
                'balance': cc_base_amount,
                'amount_currency': base_amount,
                'tax_tag_ids': [Command.set(withholding_lines._get_withholding_tax_base_tag_ids())],
            })

        payment_vals['write_off_line_vals'].append({
            'currency_id': self.currency_id.id,
            'name': _('WH Base Counterpart'),
            'account_id': tax_base_account,
            'balance': -balance_sum,
            'amount_currency': -amount_currency_sum,
        })

        return payment_vals

    def _get_withholding_tax_domain(self, company=None):
        """ Construct and return a domain that will filter withholding taxes available for this wizard. """
        self.ensure_one()
        company = company or self.company_id
        filter_domain = models.check_company_domain_parent_of(self, company)
        payment_type = 'purchases_wth' if self.payment_type == 'outbound' else 'sales_wth'
        return expression.AND([filter_domain, [('type_tax_use', '=', payment_type)]])
