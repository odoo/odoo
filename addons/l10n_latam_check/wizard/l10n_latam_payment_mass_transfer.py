from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class L10n_LatamPaymentMassTransfer(models.TransientModel):
    _name = 'l10n_latam.payment.mass.transfer'
    _description = 'Checks Mass Transfers'
    _check_company_auto = True

    company_ids = fields.Many2many(
        comodel_name='res.company',
        default=lambda self: self.env.companies,
    )
    from_journal_id = fields.Many2one(
        comodel_name='account.journal',
        check_company=True,
    )
    from_journal_currency_id = fields.Many2one(related='from_journal_id.currency_id')
    to_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        domain="[('type', 'in', ('bank', 'cash')), ('id', '!=', from_journal_id), ('currency_id', '=', from_journal_currency_id)]",
        check_company=True,
        required=True,
    )
    check_ids = fields.Many2many(
        comodel_name='l10n_latam.check',
        check_company=True,
    )
    payment_date = fields.Date(
        string="Payment Date",
        default=fields.Date.context_today,
        required=True,
    )
    communication = fields.Char(string="Memo")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        if active_model and active_model != 'l10n_latam.check':
            raise ValidationError(self.env._(
                "This action can only be used on third party checks. "
                "Please call it from the Third Party Checks menu."
            ))
        if active_model:
            checks = self.env['l10n_latam.check'].browse(self.env.context.get('active_ids', [])).exists()
            journal = self._get_source_journal(checks)
            if 'from_journal_id' in fields_list:
                res['from_journal_id'] = journal.id
            if 'check_ids' in fields_list:
                res['check_ids'] = checks.ids
        return res

    @api.constrains('check_ids', 'from_journal_id')
    def _check_source_journal(self):
        for wizard in self:
            if wizard.from_journal_id != wizard._get_source_journal(wizard.check_ids):
                raise ValidationError(self.env._("The checks must be transferred from the journal they are currently on."))

    @api.model
    def _get_source_journal(self, checks):
        """ Check that ``checks`` may be transferred together and return the journal they are on. """
        if not checks:
            raise ValidationError(self.env._("Please select the checks to transfer."))
        if any(check.payment_method_line_id.code != 'new_third_party_checks' for check in checks):
            raise ValidationError(self.env._(
                "You have selected records which are not third party checks. "
                "Please call this action from the Third Party Checks menu."
            ))
        if any(check.payment_id.state in ('draft', 'canceled') for check in checks):
            raise ValidationError(self.env._("All the selected checks must be linked to posted payments."))
        if len(checks.currency_id) > 1:
            raise ValidationError(self.env._("All the selected checks must use the same currency."))
        journal = checks.current_journal_id
        if len(journal) != 1:
            raise ValidationError(self.env._("All the selected checks must be on hand and on the same journal."))
        return journal

    def _create_payments(self):
        """ This is nedeed because we would like to create a payment of type internal transfer for each check with the
        counterpart journal and then, when posting a second payment will be created automatically """
        self.ensure_one()
        from_company = self.from_journal_id.company_id
        to_company = self.to_journal_id.company_id
        if from_company.transfer_account_id != to_company.transfer_account_id:
            raise UserError(self.env._(
                'The Inter-Banks Transfer Account of "%(source_company)s" and "%(destination_company)s" must be the '
                'same to transfer checks between them.',
                source_company=from_company.display_name,
                destination_company=to_company.display_name,
            ))
        checks = self.check_ids
        currency_id = checks[0].currency_id

        pay_method_line = self.from_journal_id._get_available_payment_method_lines('outbound').filtered(
            lambda x: x.code in ('out_third_party_checks', 'return_third_party_checks')
        )[:1]

        outbound_payment = self.env['account.payment'].create({
            'date': self.payment_date,
            'amount': sum(checks.mapped('amount')),
            'partner_id': from_company.partner_id.id,
            'payment_type': 'outbound',
            'memo': self.communication,
            'journal_id': self.from_journal_id.id,
            'currency_id': currency_id.id,
            'payment_method_line_id': pay_method_line.id if pay_method_line else False,
            'l10n_latam_move_check_ids': checks,
        })
        outbound_payment.action_post()

        inbound_payment = self.env['account.payment'].create({
            'date': self.payment_date,
            'amount': sum(checks.mapped('amount')),
            'partner_id': to_company.partner_id.id,
            'payment_type': 'inbound',
            'memo': self.communication,
            'journal_id': self.to_journal_id.id,
            'currency_id': currency_id.id,
            'l10n_latam_move_check_ids': checks,
        })

        dest_payment_method = self.to_journal_id.inbound_payment_method_line_ids.filtered(
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

        body_inbound = self.env._("This payment has been created from: ") + outbound_payment._get_html_link()
        inbound_payment.message_post(body=body_inbound)
        body_outbound = self.env._("A second payment has been created: ") + inbound_payment._get_html_link()
        outbound_payment.message_post(body=body_outbound)

        (outbound_payment.move_id.line_ids + inbound_payment.move_id.line_ids).filtered(
            lambda l:
            l.account_id == outbound_payment.destination_account_id and not l.reconciled
        ).reconcile()

        return outbound_payment

    def action_create_payments(self):
        payments = self._create_payments()
        return payments._get_records_action(name=self.env._("Payment(s)"), context={'create': False})
