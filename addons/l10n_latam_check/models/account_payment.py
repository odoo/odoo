from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_latam_new_check_ids = fields.One2many('l10n_latam.check', 'payment_id', string='New Checks')
    l10n_latam_check_ids = fields.Many2many(
        comodel_name='l10n_latam.check',
        relation='account_payment_account_payment_check_rel',
        column1="payment_id",
        column2="check_id",
        required=True,
        copy=False,
        string="Checks"
    )
    # Warning message in case of unlogical third party check operations
    l10n_latam_check_warning_msg = fields.Text(
        compute='_compute_l10n_latam_check_warning_msg',
    )
    amount = fields.Monetary(compute="_compute_amount", readonly=False, store=True)

    @api.depends('l10n_latam_check_ids.amount', 'l10n_latam_new_check_ids.amount', 'payment_method_code')
    def _compute_amount(self):
        for rec in self.filtered(lambda x: x._is_latam_check_payment(check_subtype='new_check')):
            rec.amount = sum(rec.l10n_latam_new_check_ids.mapped('amount'))
        for rec in self.filtered(lambda x: x._is_latam_check_payment(check_subtype='move_check')):
            rec.amount = sum(rec.l10n_latam_check_ids.mapped('amount'))

    def _is_latam_check_payment(self, check_subtype=False):
        if check_subtype == 'move_check':
            codes = ['in_third_party_checks', 'out_third_party_checks']
        elif check_subtype == 'new_check':
            codes = ['new_third_party_checks', 'own_checks']
        else:
            codes = ['in_third_party_checks', 'out_third_party_checks', 'new_third_party_checks', 'own_checks']
        return self.payment_method_code in codes

    def action_post(self):
        # unlink checks if payment method code is not for checks. We do it on post and not when changing payment
        # method so that the user don't loose checks data in case of changing payment method and coming back again
        # also, changing partner recompute payment method so all checks would be cleaned
        for payment in self.filtered(lambda x: x.l10n_latam_new_check_ids and not x._is_latam_check_payment(check_subtype='new_check')):
            payment.l10n_latam_new_check_ids.unlink()
        for payment in self.filtered(lambda x: x.l10n_latam_check_ids and not x._is_latam_check_payment(check_subtype='move_check')):
            payment.l10n_latam_check_ids = False
        msgs = self._get_blocking_l10n_latam_warning_msg()
        if msgs:
            raise ValidationError('* %s' % '\n* '.join(msgs))
        super().action_post()
        self._l10n_latam_check_split_move()

    def _get_latam_checks(self):
        self.ensure_one()
        if self._is_latam_check_payment(check_subtype='new_check'):
            return self.l10n_latam_new_check_ids
        elif self._is_latam_check_payment(check_subtype='move_check'):
            return self.l10n_latam_check_ids
        else:
            return self.env['l10n_latam.check']

    def _get_blocking_l10n_latam_warning_msg(self):
        msgs = []
        for rec in self.filtered(lambda x: x.state == 'draft' and x._is_latam_check_payment()):
            if any(rec.currency_id != check.currency_id for check in rec._get_latam_checks()):
                msgs.append(_('The currency of the payment and the currency of the check must be the same.'))
            if not rec.currency_id.is_zero(sum(rec._get_latam_checks().mapped('amount')) - rec.amount):
                msgs.append(_(
                    'The amount of the payment  does not match the amount of the selected check. '
                    'Please try to deselect and select the check again.'))
            # checks being moved
            if rec._is_latam_check_payment(check_subtype='move_check'):
                if any(check.state != 'posted' for check in rec.l10n_latam_check_ids):
                    msgs.append(_('Selecteds check "%s" are not posted',
                                  rec.l10n_latam_check_ids.filtered(lambda x: x.state != 'posted').mapped('display_name')))
                elif (rec.payment_type == 'outbound' and
                        any(check.current_journal_id != rec.journal_id for check in rec.l10n_latam_check_ids)) or (
                        rec.payment_type == 'inbound' and rec.is_internal_transfer and
                        any(check.current_journal_id != rec.destination_journal_id for check in rec.l10n_latam_check_ids)):
                    # check outbound payment and transfer or inbound transfer
                    msgs.append(_(
                        'Some checks are not anymore in journal, it seems it has been moved by another payment.'))
                elif rec.payment_type == 'inbound' and not rec.is_internal_transfer and \
                        any(rec.l10n_latam_check_ids.mapped('current_journal_id')):
                    msgs.append(_("Some checks are already in hand and can't be received again. Checks: %s",
                                ', '.join(rec.l10n_latam_check_ids.mapped('display_name'))))

                for check in rec.l10n_latam_check_ids:
                    date = rec.date or fields.Datetime.now()

                    last_operation = check._get_last_operation()
                    if last_operation and last_operation[0].date > date:
                        msgs.append(_(
                            "It seems you're trying to move a check with a date (%s) prior to last operation done with "
                            "the check (%s). This may be wrong, please double check it. By continue, the last operation on "
                            "the check will remain being %s",
                            format_date(self.env, date), last_operation.display_name, last_operation.display_name))

        return msgs

    def _get_reconciled_checks_error(self):
        checks_reconciled = self.l10n_latam_new_check_ids.filtered(lambda x: x.issue_state in ['debited', 'voided'])
        if checks_reconciled:
            raise UserError(_(
                "You can't cancel or re-open a payment with checks if some check has been debited or been voided. Checks:\n"
                "%s" % ('\n'.join(['* %s (%s)' % (x.name, x.issue_state) for x in checks_reconciled]))))

    def action_cancel(self):
        self._get_reconciled_checks_error()
        super().action_cancel()

    def action_draft(self):
        self._get_reconciled_checks_error()
        super().action_draft()

    def _l10n_latam_check_split_move(self):
        for payment in self.filtered(lambda x: x.payment_method_code == 'own_checks' and x.payment_type == 'outbound'):
            move_id = self.env['account.move'].create({
                'journal_id': payment.journal_id.id,
            })
            liquidity_line, dummy, dummy = payment._seek_for_lines()

            for check in payment.l10n_latam_new_check_ids:
                liquidity_amount_currency = -check.amount
                liquidity_balance = payment.currency_id._convert(
                    liquidity_amount_currency,
                    payment.company_id.currency_id,
                    payment.company_id,
                    payment.date,
                )
                # Checks liquidity line
                move_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': check.name,
                    'date_maturity': check.payment_date,
                    'amount_currency': liquidity_amount_currency,
                    'currency_id': check.currency_id.id,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                    'partner_id': payment.partner_id.id,
                    'account_id': payment.outstanding_account_id.id,
                    'move_id': move_id.id,
                })
                check.split_move_line_id = move_line.id

            # inverse liquidity line
            inverse_liquidity_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': liquidity_line.name,
                    'date_maturity': liquidity_line.date_maturity,
                    'amount_currency': -liquidity_line.amount_currency,
                    'currency_id': liquidity_line.currency_id.id,
                    'debit': -liquidity_line.debit,
                    'credit': -liquidity_line.credit,
                    'partner_id': payment.partner_id.id,
                    'account_id': payment.outstanding_account_id.id,
                    'move_id': move_id.id,
                })
            move_id.action_post()
            (inverse_liquidity_line + liquidity_line).reconcile()

    def _l10n_latam_check_unlink_split_move(self):
        split_move_ids = self.mapped('l10n_latam_new_check_ids.split_move_line_id.move_id')
        split_move_ids.button_draft()
        split_move_ids.unlink()

    @api.depends(
        'payment_method_line_id', 'state',  'date', 'is_internal_transfer', 'amount', 'currency_id', 'company_id',
        'l10n_latam_check_ids.issuer_vat', 'l10n_latam_check_ids.bank_id', 'l10n_latam_check_ids.date',
        'l10n_latam_new_check_ids.amount', 'l10n_latam_new_check_ids.name',
    )
    def _compute_l10n_latam_check_warning_msg(self):
        """
        Compute warning message for latam checks checks
        We use l10n_latam_check_number as de dependency because on the interface this is the field the user is using.
        Another approach could be to add an onchange on _inverse_l10n_latam_check_number method
        """
        self.l10n_latam_check_warning_msg = False
        for rec in self.filtered(lambda x: x._is_latam_check_payment()):
            msgs = rec._get_blocking_l10n_latam_warning_msg()
            # new third party check uniqueness warning (on own checks it's done by a sql constraint)
            if rec.payment_method_code == 'new_third_party_checks':
                same_checks = self.env['l10n_latam.check']
                for check in rec.l10n_latam_new_check_ids.filtered(
                        lambda x: x.name and x.payment_method_line_id.code == 'new_third_party_checks' and
                        x.bank_id and x.issuer_vat):
                    same_checks += same_checks.search([
                        ('company_id', '=', rec.company_id.id),
                        ('bank_id', '=', check.bank_id.id),
                        ('issuer_vat', '=', check.issuer_vat),
                        ('name', '=', check.name),
                        ('state', '=', 'posted'),
                        ('id', '!=', check._origin.id)], limit=1)
                if same_checks:
                    msgs.append(_(
                        "Other checks were found with same number, issuer and bank. Please double check you are not "
                        "encoding the same check more than once. List of other payments/checks: %s",
                        ", ".join(same_checks.mapped('display_name'))))
            rec.l10n_latam_check_warning_msg = msgs and '* %s' % '\n* '.join(msgs) or False

    @api.depends('is_internal_transfer')
    def _compute_payment_method_line_fields(self):
        """ Add is_internal_transfer as a trigger to re-compute """
        return super()._compute_payment_method_line_fields()

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()
        if self.is_internal_transfer:
            res.append('new_third_party_checks')
        return res

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_latam_check_ids',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        # check = self if (self.payment_method_line_id.code == 'new_third_party_checks' or (self.payment_method_line_id.code == 'own_printing' and self.l10n_latam_manual_checks)) \
        #     else self.l10n_latam_check_id
        if self.l10n_latam_check_ids:
            document_names = (_('Check %s received') if self.payment_type == 'inbound' else _('Check %s delivered')) % (
                     ', '.join(self.l10n_latam_check_ids.mapped('name')))
            res[0].update({
                'name': document_names + ' - ' + ''.join([item[1] for item in self._get_aml_default_display_name_list()]),
            })
        return res

    def _create_paired_internal_transfer_payment(self):
        """
        Two modifications when only when transferring from a third party checks journal:
        1. When a paired transfer is created, the default odoo behavior is to use on the paired transfer the first
        available payment method. If we are transferring to another third party checks journal, then set as payment
        method on the paired transfer 'in_third_party_checks' or 'out_third_party_checks'
        2. On the paired transfer set the l10n_latam_check_id field, this field is needed for the
        operation_ids and also for some warnings and constrains.
        """
        third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code in [
            'in_third_party_checks',
            'out_third_party_checks'
        ])
        for rec in third_party_checks:
            dest_payment_method_code = 'in_third_party_checks' if rec.payment_type == 'outbound' else 'out_third_party_checks'
            dest_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
                lambda x: x.code == dest_payment_method_code)
            if dest_payment_method:
                super(AccountPayment, rec.with_context(
                    default_payment_method_line_id=dest_payment_method.id,
                    default_l10n_latam_check_ids=rec.l10n_latam_check_ids.ids,
                ))._create_paired_internal_transfer_payment()
            else:
                super(AccountPayment, rec.with_context(
                    default_l10n_latam_check_ids=rec.l10n_latam_check_ids.ids,
                ))._create_paired_internal_transfer_payment()
        super(AccountPayment, self - third_party_checks)._create_paired_internal_transfer_payment()
