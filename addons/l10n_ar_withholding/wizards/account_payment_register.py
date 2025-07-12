# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import markupsafe
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_ar_withholding_ids = fields.One2many(
        'l10n_ar.payment.register.withholding', 'payment_register_id', string="Withholdings",
        compute="_compute_l10n_ar_withholding_ids", readonly=False, store=True)
    l10n_ar_net_amount = fields.Monetary(compute='_compute_l10n_ar_net_amount', readonly=True, help="Net amount after withholdings")
    l10n_ar_adjustment_warning = fields.Boolean(compute="_compute_l10n_ar_adjustment_warning")
    l10n_ar_fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        check_company=True,
        compute='_compute_fiscal_position_id', store=True, readonly=False,
        domain=[('l10n_ar_tax_ids.tax_type', '=', 'withholding')],
    )

    @api.depends('line_ids', 'partner_id')
    def _compute_fiscal_position_id(self):
        """Compute the fiscal position ID for the payment register wizard."""
        for rec in self:
            if rec.partner_type != 'supplier' or rec.country_code != 'AR' or not rec.can_edit_wizard or (rec.can_group_payments and not rec.group_payment):
                rec.l10n_ar_fiscal_position_id = False
                continue
            # si estamos pagando todas las facturas de misma delivery address usamos este dato para computar la
            # fiscal position
            if len(rec.batches) == 1:
                batch_result = rec.batches[0]
                addresses = batch_result['lines'].mapped('move_id.partner_shipping_id')
                if len(addresses) == 1:
                    address = addresses
                else:
                    address = rec.partner_id
            rec.l10n_ar_fiscal_position_id = self.env['account.fiscal.position'].with_company(rec.company_id).with_context(l10n_ar_withholding=True)._get_fiscal_position(
                address)

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

        if not self.l10n_ar_withholding_ids:
            return payment_vals  # Nothing to do if we are not working with withholding taxes.

        payment_vals['amount'] = self.l10n_ar_net_amount
        conversion_rate = self._get_conversion_rate()
        sign = 1
        if self.partner_type == 'supplier':
            sign = -1
        withholding_refs = ''
        for line in self.l10n_ar_withholding_ids:
            if not line.name:
                if line.tax_id.l10n_ar_withholding_sequence_id:
                    line.name = line.tax_id.l10n_ar_withholding_sequence_id.next_by_id()
                else:
                    raise UserError(_('Please enter withholding number for tax %s') % line.tax_id.name)
            _dummy, account_id, tax_repartition_line_id, withholding_ref = line._tax_compute_all_helper()
            withholding_refs += withholding_ref
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
                'tax_ids': [Command.set(withholding_lines.mapped('tax_id').ids)],
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

        payment_vals['withholding_refs'] = withholding_refs
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

    @api.depends('partner_id', 'payment_date', 'l10n_ar_fiscal_position_id')
    def _compute_l10n_ar_withholding_ids(self):
        """
        Computes the withholding tax records (`l10n_ar_withholding_ids`) for the payment register
        based on the partner, payment date, and fiscal position.
        """
        for rec in self:
            date = fields.Date.from_string(rec.payment_date) or datetime.date.today()

            withholdings = [Command.clear()]
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(rec.partner_id, rec.company_id, date, 'withholding')
                withholdings += [Command.create({'tax_id': x.id}) for x in taxes]
            rec.l10n_ar_withholding_ids = withholdings

    def action_create_payments(self):
        if self.l10n_ar_withholding_ids and not self.payment_method_line_id.payment_account_id:
            raise ValidationError(_("A payment cannot have withholding if the payment method has no outstanding accounts"))
        return super().action_create_payments()

    def _init_payments(self, to_process, edit_mode=False):
        withholding_refs = None
        if to_process and 'withholding_refs' in to_process[0].get('create_vals', {}):
            withholding_refs = to_process[0]['create_vals'].pop('withholding_refs')
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        if withholding_refs:
            message = _('Withholding computation detail: %(withholding_refs)s')
            payments.message_post(body=markupsafe.Markup(message % {'withholding_refs': withholding_refs}))
        return payments
