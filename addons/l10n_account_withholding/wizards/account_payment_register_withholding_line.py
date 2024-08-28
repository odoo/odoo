# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _name = 'account.payment.withholding.line'
    _description = 'Payment register withholding line'
    _check_company_auto = True

    # ------------------
    # Fields declaration
    # ------------------

    payment_register_id = fields.Many2one(
        comodel_name='account.payment.register',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='payment_register_id.company_id')
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    custom_user_currency_id = fields.Many2one(comodel_name='res.currency')
    partner_type = fields.Selection(related='payment_register_id.partner_type')
    can_edit_wizard = fields.Boolean(related='payment_register_id.can_edit_wizard')
    payment_date = fields.Date(related='payment_register_id.payment_date')
    invoice_amount_total = fields.Monetary(related='payment_register_id.l10n_account_withholding_payment_invoice_amount_total')
    name = fields.Char(string='Sequence Number')
    type_tax_use = fields.Char(compute='_compute_type_tax_use')
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        required=True,
        domain="[('type_tax_use', '=', type_tax_use)]"
    )
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_account_withholding_sequence_id')
    full_base_amount = fields.Monetary(required=True)
    full_base_amount_in_currency = fields.Monetary(required=True, compute='_compute_full_base_amount_in_currency')
    custom_user_amount = fields.Monetary()
    base_amount = fields.Monetary(
        required=True,
        compute='_compute_base_amount',
        precompute=True,
        readonly=False,
        store=True,
    )
    amount = fields.Monetary(
        string='Withheld Amount',
        compute='_compute_amount',
        store=True,
        readonly=False
    )

    # ----------------
    # Business methods
    # ----------------

    def _get_withholding_tax_values(self):
        """ Helper that uses compute_all in order to return the detail

        :returns: a dict with the amount, account and tax_repartition_line keys.
        """
        self.ensure_one()
        # One line will always have a single tax.
        tax_values = self.tax_id.compute_all(price_unit=self.base_amount, currency=self.currency_id)['taxes'][0]
        return {
            'amount': tax_values['amount'],
            'account': tax_values['account_id'],
            'tax_repartition_line': tax_values['tax_repartition_line_id'],
            'tax_name': tax_values['name'],
            'tax_base_amount': tax_values['base'],
            'tag_ids': tax_values['tag_ids'],
        }

    def _get_withholding_tax_base_tag_ids(self):
        tag_ids = set()
        for line in self:
            tax_values = line.tax_id.compute_all(price_unit=line.base_amount, currency=line.currency_id)
            tag_ids.update(tax_values['base_tags'])
        return tag_ids

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = line._get_withholding_tax_values()['amount']

    @api.depends('payment_register_id')
    def _compute_type_tax_use(self):
        for line in self:
            line.type_tax_use = 'sales_wth' if line.partner_type == 'customer' else 'purchases_wth'

    @api.depends('full_base_amount', 'currency_id')
    def _compute_full_base_amount_in_currency(self):
        """ full_base_amount is the amount in the company currency.
        If the wizard currency differs from that amount, we need to ensure that we adapt the withholding amounts as well.
        """
        for line in self:
            line.full_base_amount_in_currency = line.company_id.currency_id._convert(
                line.full_base_amount,
                line.currency_id,
                line.company_id,
                line.payment_date,
            )

    @api.depends('full_base_amount_in_currency', 'payment_register_id.amount')
    def _compute_base_amount(self):
        """ We want the base amount of our withholding line to be adapted to installments/... for the default value.
        As we don't want to duplicate the whole logic of payment terms/installment and recompute everything, we'll simply
        find out how much % of the full price we are paying in this payment, and apply that ratio to the amount.
        """
        for line in self:
            # In practice, we'll always want that default value to be computed based on a ratio of what is being paid.
            if not line.custom_user_amount:
                line.base_amount = line.full_base_amount_in_currency * line._get_payment_ratio()
            else:
                line.base_amount = line.custom_user_amount

    @api.onchange('base_amount')
    def _onchange_base_amount(self):
        """ Check if the user has input a custom amount; if so we don't want to recompute it automatically. """
        if not self.can_edit_wizard or not self.currency_id:
            return

        is_custom_user_amount = self.base_amount != (self.full_base_amount_in_currency * self._get_payment_ratio())
        if is_custom_user_amount:
            self.custom_user_amount = self.base_amount
            self.custom_user_currency_id = self.currency_id
        else:
            self.custom_user_amount = None
            self.custom_user_currency_id = None

    def _get_payment_ratio(self):
        """ I some cases, we need to know how much % of the full amount we're paying for.
        This is useful when using installments, or also when paying in multiple time, as we want to be able to
        give a default withholding base amount which make sense for the current payment.

        This method is there to help for that by providing a ratio to multiply the full_base_amount with to get
        that wanted amount.
        """
        # We can't and it wouldn't make sense to try and adapt lines on a manual payment.
        if not self.invoice_amount_total:
            return 1

        # We are working with amounts in currency in this context, so we need to make sure to convert this amount
        # which is in company currency into the wizard currency.
        total_amount_in_currency = self.company_id.currency_id._convert(
            self.invoice_amount_total,
            self.currency_id,
            self.company_id,
            self.payment_date,
        )
        return self.payment_register_id.amount / total_amount_in_currency
