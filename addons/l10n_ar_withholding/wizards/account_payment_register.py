# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_ar_withholding_ids = fields.One2many(
        'l10n_ar.payment.register.withholding', 'payment_register_id', string="Withholdings",
        compute="_compute_l10n_ar_withholding_ids", readonly=False, store=True)
    l10n_ar_net_amount = fields.Monetary(compute='_compute_l10n_ar_net_amount', readonly=True, help="Net amount after withholdings")
    l10n_ar_adjustment_warning = fields.Boolean(compute="_compute_l10n_ar_adjustment_warning")

    @api.depends('l10n_latam_move_check_ids.amount', 'amount', 'l10n_ar_net_amount', 'l10n_latam_new_check_ids.amount', 'payment_method_code')
    def _compute_l10n_ar_adjustment_warning(self):
        wizard_register = self
        for wizard in self:
            checks = wizard.l10n_latam_new_check_ids if wizard.filtered(lambda x: x._is_latam_check_payment(check_subtype='new_check')) else wizard.l10n_latam_move_check_ids
            checks_amount = sum(checks.mapped('amount'))
            if checks_amount and wizard.l10n_ar_net_amount != checks_amount:
                wizard.l10n_ar_adjustment_warning = True
                wizard_register -= wizard
        wizard_register.l10n_ar_adjustment_warning = False

    @api.depends('amount', 'l10n_ar_withholding_ids.amount')
    def _compute_l10n_ar_net_amount(self):
        for rec in self:
            rec.l10n_ar_net_amount = rec.amount - sum(rec.l10n_ar_withholding_ids.mapped('amount'))

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['amount'] = self.l10n_ar_net_amount
        conversion_rate = self._get_conversion_rate()
        sign = 1
        if self.partner_type == 'supplier':
            sign = -1
        for line in self.l10n_ar_withholding_ids:
            if not line.name:
                if line.tax_id.l10n_ar_withholding_sequence_id:
                    line.name = line.tax_id.l10n_ar_withholding_sequence_id.next_by_id()
                else:
                    raise UserError(_('Please enter withholding number for tax %s') % line.tax_id.name)
            dummy, account_id, tax_repartition_line_id = line._tax_compute_all_helper()
            balance = self.company_currency_id.round(line.amount * conversion_rate)
            # create withholding amount applied move line only if amount != 0
            payment_vals['write_off_line_vals'].append({
                    'currency_id': self.currency_id.id,
                    'name': line.name,
                    'account_id': account_id,
                    'amount_currency': sign * line.amount,
                    'balance': sign * balance,
                    'tax_base_amount': sign * line.base_amount,
                    'tax_repartition_line_id': tax_repartition_line_id,
            })

        for base_amount in list(set(self.l10n_ar_withholding_ids.mapped('base_amount'))):
            withholding_lines = self.l10n_ar_withholding_ids.filtered(lambda x: x.base_amount == base_amount)
            nice_base_label = ','.join(withholding_lines.mapped('name'))
            account_id = self.company_id.l10n_ar_tax_base_account_id.id
            base_amount = sign * base_amount
            cc_base_amount = self.company_currency_id.round(base_amount * conversion_rate)
            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,
                'name': nice_base_label,
                'tax_ids': [Command.set(withholding_lines.tax_id.ids)],
                'account_id': account_id,
                'balance': cc_base_amount,
                'amount_currency': base_amount,
            })
            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,  # Counterpart 0 operation
                'name': nice_base_label,
                'account_id': account_id,
                'balance': -cc_base_amount,
                'amount_currency': -base_amount,
            })

        return payment_vals

    def _get_conversion_rate(self):
        self.ensure_one()
        if self.currency_id != self.company_id.currency_id:
            return self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                self.company_id.currency_id,
                self.company_id,
                self.payment_date,
            )
        return 1.0

    @api.depends('partner_id', 'payment_date')
    def _compute_l10n_ar_withholding_ids(self):
        for wizard in self:
            date = wizard.payment_date or fields.Date.context_today(self)
            partner_taxes = self.env['l10n_ar.partner.tax'].search([
                *self.env['l10n_ar.partner.tax']._check_company_domain(wizard.company_id),
                '|', ('from_date', '>=', date), ('from_date', '=', False),
                '|', ('to_date', '<=', date), ('to_date', '=', False),
                ('partner_id', '=', wizard.partner_id.commercial_partner_id.id),
                ('tax_id.l10n_ar_withholding_payment_type', '=', wizard.partner_type)
            ])
            wizard.l10n_ar_withholding_ids = [Command.clear()] + [Command.create({'tax_id': x.tax_id.id}) for x in partner_taxes]

    def action_create_payments(self):
        if self.l10n_ar_withholding_ids and not self.payment_method_line_id.payment_account_id:
            raise ValidationError(_("A payment cannot have withholding if the payment method has no outstanding accounts"))
        return super().action_create_payments()
