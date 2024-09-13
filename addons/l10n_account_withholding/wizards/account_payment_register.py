# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_line_ids = fields.One2many(
        string="Withholding Lines",
        comodel_name='account.payment.register.withholding.line',
        inverse_name='payment_register_id',
        compute='_compute_from_lines',
        store=True,
        readonly=False,
    )
    l10n_account_withholding_net_amount = fields.Monetary(
        string='Net Amount',
        help="Net amount after deducting the withholding lines",
        compute='_compute_l10n_account_withholding_net_amount',
        readonly=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('l10n_account_withholding_line_ids.amount', 'amount')
    def _compute_l10n_account_withholding_net_amount(self):
        for wizard in self:
            wizard.l10n_account_withholding_net_amount = wizard.amount - sum(wizard.l10n_account_withholding_line_ids.mapped('amount'))

    # ----------------
    # Business methods
    # ----------------

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
            withholding_line_creation_vals = []
            if wizard.can_edit_wizard:
                withholding_line_amounts = defaultdict(int)
                batch_result = wizard.batches[0]
                for move in batch_result['lines'].move_id:
                    filter_domain = self.env['account.tax']._check_company_domain(move.company_id)
                    for line in move.invoice_line_ids:
                        withholding_taxes = None
                        if move.is_sale_document(include_receipts=True):
                            filter_domain = expression.AND([
                                filter_domain,
                                [('l10n_account_withholding_type', '=', 'customer')],
                            ])
                            withholding_taxes = line.product_id.taxes_id.filtered_domain(filter_domain)
                        elif move.is_purchase_document(include_receipts=True):
                            filter_domain = expression.AND([
                                filter_domain,
                                [('l10n_account_withholding_type', '=', 'supplier')],
                            ])
                            withholding_taxes = line.product_id.supplier_taxes_id.filtered_domain(filter_domain)
                        for withholding_tax in withholding_taxes:
                            # Check if the move has a fiscal position and apply if needed.
                            if move.fiscal_position_id:
                                withholding_tax = move.fiscal_position_id.map_tax(withholding_tax)
                            withholding_line_amounts[withholding_tax] += abs(line.balance)  # The base amount is always a positive amount

                for withholding_tax, withholding_line_amount in withholding_line_amounts.items():
                    tax_amount = withholding_tax.compute_all(price_unit=withholding_line_amount, currency=self.currency_id)['taxes'][0]['amount']
                    withholding_line_creation_vals.append(Command.create({
                        'company_id': wizard.company_id.id,
                        'currency_id': wizard.currency_id.id,
                        'tax_id': withholding_tax.id,
                        'base_amount': withholding_line_amount,
                        'amount': tax_amount,
                    }))
            wizard.l10n_account_withholding_line_ids = withholding_line_creation_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        # EXTEND account
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        if not self.l10n_account_withholding_line_ids:
            return payment_vals  # Nothing to do if we are not working with withholding taxes.

        # Get the account set on the company; raise an error if not set.
        tax_base_account = self.company_id.l10n_account_withholding_tax_base_account_id.id
        if not tax_base_account:
            raise UserError(_('To register withholding taxes, the "Withholding Tax Base Account" must be set in the settings.'))
        # The payment amount is the base amount set in the wizard, minus the sum of the withholding line amounts.
        payment_vals['amount'] = self.l10n_account_withholding_net_amount
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
                'name': withholding_line.name,
                'account_id': tax_account,
                'amount_currency': sign * withholding_line.amount,
                'balance': sign * self.company_currency_id.round(withholding_line.amount * conversion_rate),
                'tax_base_amount': withholding_tax_values['tax_base_amount'],
                'tax_repartition_line_id': withholding_tax_values['tax_repartition_line'],
            })

        # We also need tax base lines for reporting. We simply create one per unique base amount.
        for base_amount, withholding_lines in self.l10n_account_withholding_line_ids.grouped('base_amount').items():
            withholding_numbers = ','.join(withholding_lines.mapped('name'))
            base_amount = sign * base_amount
            cc_base_amount = self.company_currency_id.round(base_amount * conversion_rate)
            # The aim is to get one base line with the correct amount, and a counterpart that cancels it.
            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,
                'name': _('Withholding Base For: %(withholding_numbers)s', withholding_numbers=withholding_numbers),
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
                'account_id': tax_base_account,
                'balance': cc_base_amount,
                'amount_currency': base_amount,
            })
            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,
                'name': _('Withholding Base Counterpart For: %(withholding_numbers)s', withholding_numbers=withholding_numbers),
                'account_id': tax_base_account,
                'balance': -cc_base_amount,
                'amount_currency': -base_amount,
            })

        return payment_vals
