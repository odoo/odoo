# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_ar_withholding_ids = fields.One2many(
        'l10n_ar.payment.register.withholding', 'payment_register_id', string="Withholdings",
        compute='_compute_withholdings', readonly=False, store=True)
    l10n_ar_net_amount = fields.Monetary(compute='_compute_l10n_ar_net_amount', readonly=True,  help="Net amount after withholdings")

    @api.depends('line_ids', 'can_group_payments', 'group_payment')
    def _compute_withholdings(self):
        supplier_recs = self.filtered(lambda x: x.partner_type == 'supplier' and (not x.can_group_payments or (x.can_group_payments and x.group_payment)))
        for rec in supplier_recs:
            taxes = rec._get_withholding_tax()
            rec.l10n_ar_withholding_ids = [Command.clear()] + [Command.create({'tax_id': x.id, 'base_amount': 0}) for x in taxes]
        (self - supplier_recs).l10n_ar_withholding_ids = False

    # @api.depends('l10n_latam_check_id', 'l10n_ar_withholding_ids.amount')
    # def _compute_amount(self):
    #     super()._compute_amount()
    #     for wizard in self.filtered(lambda x: x.l10n_ar_withholding_ids and x.l10n_latam_check_id):
    #         wizard.currency_id = wizard.l10n_latam_check_id.currency_id
    #         wizard.l10n_ar_net_amount = wizard.l10n_latam_check_id.amount
    #         factor, net_amount = wizard._get_amount_net_info()
    #         withholding_net_amount = min(wizard.l10n_latam_check_id.amount , net_amount)
    #         wizard.amount = withholding_net_amount * factor + (wizard.l10n_latam_check_id.amount - withholding_net_amount)

    @api.depends('l10n_ar_withholding_ids.amount', 'amount', 'l10n_latam_check_id')
    def _compute_l10n_ar_net_amount(self):
        for rec in self:
            if rec.l10n_latam_check_id:
                rec.currency_id = rec.l10n_latam_check_id.currency_id
                rec.l10n_ar_net_amount = rec.l10n_latam_check_id.amount
                factor, net_amount = rec._get_amount_net_info()
                withholding_net_amount = min(rec.l10n_latam_check_id.amount , net_amount)
                rec.amount = withholding_net_amount * factor + (rec.l10n_latam_check_id.amount - withholding_net_amount)
            else:
                rec.l10n_ar_net_amount = rec.amount - sum(rec.l10n_ar_withholding_ids.mapped('amount'))


    def _get_withholding_tax(self):
        self.ensure_one()
        return self.line_ids.move_id.invoice_line_ids.product_id.l10n_ar_supplier_withholding_taxes_ids.filtered(
                lambda y: y.company_id == self.company_id)

    def _get_amount_net_info(self):
        self.ensure_one()
        # This method allows to simulate the total net amount of a payment and the relationship between the total and net amounts.
        # return a tupple
        #   - factor between total and net
        #   - Net amount total
        wizard = self.env['account.payment.register'].with_context(active_model='account.move.line', active_ids=self.line_ids.ids).new()
        wizard.currency_id = self.l10n_latam_check_id.currency_id
        wizard.payment_date = self.payment_date
        wizard.l10n_ar_withholding_ids = [Command.clear()] + [Command.create({'tax_id': x.tax_id.id, 'base_amount': x.base_amount , 'amount': x.amount}) for x in self.l10n_ar_withholding_ids]
        return (wizard.amount / wizard.l10n_ar_net_amount, wizard.l10n_ar_net_amount)

    def _get_withholding_move_line_default_values(self):
        return {
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
        }

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
                    **self._get_withholding_move_line_default_values(),
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
                **self._get_withholding_move_line_default_values(),
                'name': _('Base Ret: ') + nice_base_label,
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
                'account_id': account_id,
                'balance': cc_base_amount,
                'amount_currency': base_amount,
            })
            payment_vals['write_off_line_vals'].append({
                **self._get_withholding_move_line_default_values(),  # Counterpart 0 operation
                'name': _('Base Ret Cont: ') + nice_base_label,
                'account_id': account_id,
                'balance': -cc_base_amount,
                'amount_currency': -base_amount,
            })

        return payment_vals

    def _get_conversion_rate(self):
        self.ensure_one()
        if  self.currency_id !=  self.source_currency_id:
            return self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                self.source_currency_id,
                self.company_id,
                self.payment_date,
            )
        return  1.0

    def _l10n_ar_get_payment_factor(self):
        # The factor represents the portion of the invoiced amount that I am paying and is used to calculate
        # the base amount. When pay more than billed, the factor is 1, because I should only pay tax on the invoiced amount.
        # billed | payment | factor
        #    100 |      50 |    0.5
        #    100 |     100 |      1
        #    100 |     200 |      1

        self.ensure_one()
        amount_total = sum([m.amount_total for m in self.mapped('line_ids.move_id')])
        conversion_rate = self._get_conversion_rate()
        real_amount = min(self.amount, self.source_amount / conversion_rate)
        return min((real_amount * conversion_rate) / amount_total, 1)
