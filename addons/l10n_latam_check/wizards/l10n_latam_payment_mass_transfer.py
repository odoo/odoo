# -*- coding: utf-8 -*-

from odoo import models, api, fields, _, Command
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
    communication = fields.Char(string="Memo")
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
        'l10n_latam.check', 'latam_tranfer_check_rel'
        'transfer_id', 'check_id', check_company=True,
    )

    @api.depends('check_ids')
    def _compute_journal_company(self):
        # use ._origin because if not a NewId for the checks is used and the returned
        # value for current_journal_id is wrong
        journal = self.check_ids._origin.mapped("current_journal_id")
        if len(journal) != 1:
            raise UserError(_("All selected checks must be on the same journal and on hand"))
        self.journal_id = journal
        self.company_id = journal.company_id.id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'check_ids' in fields_list and 'check_ids' not in res:
            if self._context.get('active_model') != 'l10n_latam.check':
                raise UserError(_("The register payment wizard should only be called on account.payment records."))
            checks = self.env['l10n_latam.check'].browse(self._context.get('active_ids', []))
            if checks.filtered(lambda x: x.payment_method_line_id.code != 'new_third_party_checks'):
                raise 'You have select some payments that are not checks. Please call this action from the Third Party Checks menu'
            elif not all(check.payment_id.state != 'draft' for check in checks):
                raise UserError(_("All the selected checks must be posted"))
            currency_ids = checks.mapped('currency_id')
            if any(x != currency_ids[0] for x in currency_ids):
                raise UserError(_("All the selected checks must use the same currency"))
            res['check_ids'] = checks.ids
        return res

    def _create_payments(self):
        """ This is nedeed because we would like to create a payment of type internal transfer for each check with the
        counterpart journal and then, when posting a second payment will be created automatically """
        self.ensure_one()
        checks = self.check_ids.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks' and x.currency_id == self.check_ids[0].currency_id)
        currency_id = self.check_ids[0].currency_id

        pay_method_line = self.journal_id._get_available_payment_method_lines('outbound').filtered(
            lambda x: x.code in ('out_third_party_checks', 'return_third_party_checks')
        )[:1]

        outbound_payment = self.env['account.payment'].create({
            'date': self.payment_date,
            'amount': sum(checks.mapped('amount')),
            'partner_id': self.env.company.partner_id.id,
            'payment_type': 'outbound',
            'memo': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': currency_id.id,
            'payment_method_line_id': pay_method_line.id if pay_method_line else False,
            'l10n_latam_move_check_ids': [Command.link(x.id) for x in checks],
        })
        outbound_payment.action_post()

        inbound_payment = self.env['account.payment'].create({
            'date': self.payment_date,
            'amount': sum(checks.mapped('amount')),
            'partner_id': self.env.company.partner_id.id,
            'payment_type': 'inbound',
            'memo': self.communication,
            'journal_id': self.destination_journal_id.id,
            'currency_id': currency_id.id,
            'l10n_latam_move_check_ids': [Command.link(x.id) for x in checks],
        })

        dest_payment_method = self.destination_journal_id.inbound_payment_method_line_ids.filtered(
            lambda x: x.code == 'in_third_party_checks'
        )
        if dest_payment_method:
            inbound_payment.payment_method_line_id = dest_payment_method
            inbound_payment.action_post()
        else:
            # In case the journal is not part of the third party check, when posting the move we remove the checks
            # when the payment method line is not for checks, but in this case, we don't want to remove it so that
            # the operation_ids is filled with the two payments
            inbound_payment.with_context(l10n_ar_skip_remove_check=True).action_post()

        body_inbound = _("This payment has been created from: ") + outbound_payment._get_html_link()
        inbound_payment.message_post(body=body_inbound)
        body_outbound = _("A second payment has been created: ") + inbound_payment._get_html_link()
        outbound_payment.message_post(body=body_outbound)

        (outbound_payment.move_id.line_ids + inbound_payment.move_id.line_ids).filtered(
            lambda l:
            l.account_id == outbound_payment.destination_account_id and not l.reconciled
        ).reconcile()

        return outbound_payment

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
                'view_mode': 'list,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action
