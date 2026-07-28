# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class L10nLatamPaymentMassTransfer(models.TransientModel):
    _name = 'l10n_latam.payment.mass.transfer'
    _description = 'Checks Mass Transfers'
    _check_company_auto = True

    payment_date = fields.Date(
        string="Payment Date",
        required=True,
        default=fields.Date.context_today,
    )
    destination_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash')), ('id', '!=', journal_id)]",
    )
    communication = fields.Char(
        string="Memo",
    )
    journal_id = fields.Many2one(
        'account.journal',
        check_company=True,
        compute='_compute_journal_company'
    )
    company_id = fields.Many2one(
        'res.company',
        compute="_compute_journal_company"
    )
    check_ids = fields.Many2many(
        'account.payment',
        check_company=True,
    )

    @api.depends('check_ids')
    def _compute_journal_company(self):
        # use ._origin because if not a NewId for the checks is used and the returned
        # value for l10n_latam_check_current_journal_id is wrong
        journal = self.check_ids._origin.mapped("l10n_latam_check_current_journal_id")
        if len(journal) != 1 or not journal.inbound_payment_method_line_ids.filtered(
           lambda x: x.code == 'in_third_party_checks'):
            raise UserError(_("All selected checks must be on the same journal and on hand"))
        self.journal_id = journal
        self.company_id = journal.company_id.id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'check_ids' in fields_list and 'check_ids' not in res:
            if self._context.get('active_model') != 'account.payment':
                raise UserError(_("The register payment wizard should only be called on account.payment records."))
            checks = self.env['account.payment'].browse(self._context.get('active_ids', []))
            if checks.filtered(lambda x: x.payment_method_line_id.code != 'new_third_party_checks'):
                raise 'You have select some payments that are not checks. Please call this action from the Third Party Checks menu'
            elif not all(check.state == 'posted' for check in checks):
                raise UserError(_("All the selected checks must be posted"))
            res['check_ids'] = checks.ids
        return res

    def _create_payments(self):
        """ This is nedeed because we would like to create a payment of type internal transfer for each check with the
        counterpart journal and then, when posting a second payment will be created automatically """
        self.ensure_one()
        checks = self.check_ids.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
        payment_vals_list = []

        pay_method_line = self.journal_id._get_available_payment_method_lines('outbound').filtered(
            lambda x: x.code == 'out_third_party_checks')

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
                'payment_method_line_id': pay_method_line.id,
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
