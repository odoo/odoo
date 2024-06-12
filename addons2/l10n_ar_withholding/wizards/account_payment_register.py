# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_ar_withholding_ids = fields.One2many('l10n_ar.payment.register.withholding', 'payment_register_id', string="Withholdings")
    l10n_ar_net_amount = fields.Monetary(compute='_compute_l10n_ar_net_amount', readonly=True, help="Net amount after withholdings")
    l10n_ar_adjustment_warning = fields.Boolean(compute="_compute_l10n_ar_adjustment_warning")

    @api.depends('l10n_latam_check_id', 'amount', 'l10n_ar_net_amount')
    def _compute_l10n_ar_adjustment_warning(self):
        for rec in self:
            if rec.l10n_latam_check_id and rec.l10n_ar_net_amount != rec.l10n_latam_check_id.amount:
                rec.l10n_ar_adjustment_warning = True
            else:
                rec.l10n_ar_adjustment_warning = False

    @api.depends('l10n_ar_withholding_ids.amount', 'amount')
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
                'name': _('Base Ret: ') + nice_base_label,
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
                'account_id': account_id,
                'balance': cc_base_amount,
                'amount_currency': base_amount,
            })
            payment_vals['write_off_line_vals'].append({
                'currency_id': self.currency_id.id,  # Counterpart 0 operation
                'name': _('Base Ret Cont: ') + nice_base_label,
                'account_id': account_id,
                'balance': -cc_base_amount,
                'amount_currency': -base_amount,
            })

        return payment_vals

    def _get_conversion_rate(self):
        self.ensure_one()
        if self.currency_id != self.source_currency_id:
            return self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                self.source_currency_id,
                self.company_id,
                self.payment_date,
            )
        return 1.0
