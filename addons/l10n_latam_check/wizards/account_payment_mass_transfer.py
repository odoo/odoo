# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountPaymentMassTransfer(models.TransientModel):
    _name = 'account.payment.mass.transfer'
    _description = 'Checks Mass Transfers'

    payment_date = fields.Date(string="Payment Date", required=True, default=fields.Date.context_today)
    destination_journal_id = fields.Many2one(
        comodel_name='account.journal', string='Destination Journal', check_company=True,
        domain="[('type', 'in', ('bank','cash')), ('company_id', '=', company_id), ('id', '!=', journal_id)]",
    )
    company_id = fields.Many2one(related='journal_id.company_id')
    communication = fields.Char(string="Memo")
    journal_id = fields.Many2one('account.journal', readonly=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('active_model') != 'account.payment':
            raise UserError(_("The register payment wizard should only be called on account.payment records."))
        payments = self.env['account.payment'].browse(self._context.get('active_ids', []))
        checks = payments.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        if not all(check.state == 'posted' for check in checks):
            raise UserError(_("All the selected checks must be posted"))
        if len(checks.mapped('journal_id')) != 1:
            raise UserError(_("All selected checks must be on the same journal"))
        res['journal_id'] = checks[0].journal_id.id
        return res

    def _create_payments(self):
        self.ensure_one()
        payments = self.env['account.payment'].browse(self._context.get('active_ids', []))
        checks = payments.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        payment_vals_list = []
        for check in checks:
            payment_vals_list.append({
                'date': self.payment_date,
                'l10n_latam_check_id': check.id,
                'amount': check.amount,
                'payment_type': 'outbound',
                'ref': self.communication,
                'journal_id': self.journal_id.id,
                'currency_id': check.currency_id.id,
                'is_internal_transfer': True,
                'payment_method_line_id': self.env.ref('l10n_latam_check.account_payment_method_out_third_checks').id,
                'destination_journal_id': self.destination_journal_id.id,
            })
        payments = self.env['account.payment'].create(payment_vals_list)
        payments.action_post()
        return payments

    def action_create_payments(self):
        payments = self._create_payments()

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action
