# pylint: disable=protected-access
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class l10nArPaymentRegisterWithholding(models.TransientModel):
    _name = 'l10n_ar.payment.register.withholding'
    _description = 'Payment register withholding lines'
    _check_company_auto = True

    payment_register_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='payment_register_id.company_id')
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    name = fields.Char(string='Number')
    tax_id = fields.Many2one(
        'account.tax', check_company=True, required=True,
        domain="[('l10n_ar_withholding_payment_type', '=', parent.partner_type)]")
    withholding_sequence_id = fields.Many2one(related='tax_id.l10n_ar_withholding_sequence_id')
    base_amount = fields.Monetary(required=True, compute='_compute_base_amount', store=True, readonly=False)
    amount = fields.Monetary(required=True, compute='_compute_amount', store=True, readonly=False)

    def _tax_compute_all_helper(self):
        self.ensure_one()
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100

        # ARCA scales amounts are in ARS, explicitly convert amount to it to avoid summing apples and pears
        ars_currency = self.env.ref('base.ARS')
        to_date = self.payment_register_id.payment_date or datetime.date.today()
        net_amount = self.currency_id._convert(
            from_amount=self.base_amount,
            to_currency=ars_currency,
            company=self.company_id,
            date=to_date,
        )
        # if it is earnings withholding, then we accumulate the tax base for the period
        if self.tax_id.l10n_ar_tax_type in ['earnings', 'earnings_scale']:
            from_date = to_date + relativedelta(day=1)
            # We search for the payments in the same month of the same regimen and the same code.
            domain_same_period_withholdings = [
                ('company_id', 'child_of', self.tax_id.company_id.id),
                ('parent_state', '=', 'posted'),
                ('tax_line_id.l10n_ar_code', '=', self.tax_id.l10n_ar_code),
                ('tax_line_id.l10n_ar_tax_type', 'in', ['earnings', 'earnings_scale']),
                ('partner_id', '=', self.payment_register_id.partner_id.commercial_partner_id.id),
                ('date', '<=', to_date), ('date', '>=', from_date)]
            if same_period_partner_withholdings := self.env['account.move.line'].sudo()._read_group(domain_same_period_withholdings, ['partner_id'], ['balance:sum']):
                same_period_withholdings = abs(same_period_partner_withholdings[0][1])
            else:
                same_period_withholdings = 0.0
            domain_same_period_base = [
                ('company_id', 'child_of', self.tax_id.company_id.id),
                ('parent_state', '=', 'posted'),
                ('tax_ids.l10n_ar_code', '=', self.tax_id.l10n_ar_code),
                ('tax_ids.l10n_ar_tax_type', 'in', ['earnings', 'earnings_scale']),
                ('partner_id', '=', self.payment_register_id.partner_id.commercial_partner_id.id),
                ('date', '<=', to_date), ('date', '>=', from_date)]
            if same_period_partner_base := self.env['account.move.line'].sudo()._read_group(domain_same_period_base, ['partner_id'], ['balance:sum']):
                same_period_base = abs(same_period_partner_base[0][1])
            else:
                same_period_base = 0.0
            same_period_base_ars = self.currency_id._convert(
                from_amount=same_period_base,
                to_currency=ars_currency,
                company=self.company_id,
                date=to_date,
            )
            net_amount = net_amount + same_period_base_ars
        net_amount = max(0, net_amount - self.tax_id.l10n_ar_non_taxable_amount)
        taxes_res = self.tax_id.compute_all(
            net_amount,
            currency=ars_currency,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
            rounding_method='round_per_line',
        )
        tax_amount = taxes_res['taxes'][0]['amount']
        tax_account_id = taxes_res['taxes'][0]['account_id']
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']

        if self.tax_id.l10n_ar_tax_type in ['earnings', 'earnings_scale']:
            # if it is earnings scale we calculate according to the scale.
            if self.tax_id.l10n_ar_tax_type == 'earnings_scale':
                escala = self.env['l10n_ar.earnings.scale.line'].search([
                    ('scale_id', '=', self.tax_id.l10n_ar_scale_id.id),
                    ('excess_amount', '<=', net_amount),
                    ('to_amount', '>', net_amount),
                ], limit=1)
                tax_amount = ((net_amount - escala.excess_amount) * escala.percentage / 100) + escala.fixed_amount
            # deduct withholdings from the same period
            tax_amount -= same_period_withholdings

        l10n_ar_minimum_threshold = self.tax_id.l10n_ar_minimum_threshold
        if l10n_ar_minimum_threshold > tax_amount:
            tax_amount = 0.0
        # Convert back to the expected currency
        tax_amount = ars_currency._convert(
            from_amount=tax_amount,
            to_currency=self.currency_id,
            company=self.company_id,
            date=to_date,
        )
        return tax_amount, tax_account_id, tax_repartition_line_id

    @api.depends('base_amount', 'tax_id')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = line._tax_compute_all_helper()[0]

    @api.depends('payment_register_id.amount', 'tax_id')
    def _compute_base_amount(self):
        for wth in self:
            if wth.tax_id.l10n_ar_tax_type == 'iibb_total':
                wth.base_amount = wth.payment_register_id.amount
            else:
                wth.base_amount = wth.payment_register_id.amount * sum(wth.payment_register_id.line_ids.mapped('move_id.amount_untaxed')) / sum(wth.payment_register_id.line_ids.mapped("move_id.amount_total"))
