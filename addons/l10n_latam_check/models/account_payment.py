from odoo import fields, models, api, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_latam_new_check_ids = fields.One2many('l10n_latam.check', 'payment_id', string='Checks')
    l10n_latam_move_check_ids = fields.Many2many(
        comodel_name='l10n_latam.check',
        relation='l10n_latam_check_account_payment_rel',
        column1="payment_id",
        column2="check_id",
        required=True,
        copy=False,
        string="Checks Operations"
    )
    # Warning message in case of unlogical third party check operations
    l10n_latam_check_warning_msg = fields.Text(compute='_compute_l10n_latam_check_warning_msg')
    amount = fields.Monetary(compute="_compute_amount", readonly=False, store=True)

    @api.constrains('state', 'move_id')
    def _check_move_id(self):
        for payment in self:
            if (
                not payment.move_id and
                payment.payment_method_code in ('own_checks', 'new_third_party_checks', 'in_third_party_checks', 'out_third_party_checks', 'return_third_party_checks') and
                not payment.outstanding_account_id
            ):
                raise ValidationError(_("A payment with any Third Party Check or Own Check payment methods needs an outstanding account"))

    @api.depends('l10n_latam_move_check_ids.amount', 'l10n_latam_new_check_ids.amount', 'payment_method_code')
    def _compute_amount(self):
        for rec in self:
            checks = rec.l10n_latam_new_check_ids if rec._is_latam_check_payment(check_subtype='new_check') else rec.l10n_latam_move_check_ids
            if checks:
                rec.amount = sum(checks.mapped('amount'))

    def _is_latam_check_payment(self, check_subtype=False):
        if check_subtype == 'move_check':
            codes = ['in_third_party_checks', 'out_third_party_checks', 'return_third_party_checks']
        elif check_subtype == 'new_check':
            codes = ['new_third_party_checks', 'own_checks']
        else:
            codes = ['in_third_party_checks', 'out_third_party_checks', 'return_third_party_checks', 'new_third_party_checks', 'own_checks']
        return self.payment_method_code in codes

    def action_post(self):
        # unlink checks if payment method code is not for checks. We do it on post and not when changing payment
        # method so that the user don't loose checks data in case of changing payment method and coming back again
        # also, changing partner recompute payment method so all checks would be cleaned
        for payment in self.filtered(lambda x: x.l10n_latam_new_check_ids and not x._is_latam_check_payment(check_subtype='new_check')):
            payment.l10n_latam_new_check_ids.unlink()
        if not self.env.context.get('l10n_ar_skip_remove_check'):
            for payment in self.filtered(lambda x: x.l10n_latam_move_check_ids and not x._is_latam_check_payment(check_subtype='move_check')):
                payment.l10n_latam_move_check_ids = False
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
            return self.l10n_latam_move_check_ids
        else:
            return self.env['l10n_latam.check']

    def _get_blocking_l10n_latam_warning_msg(self):
        msgs = []
        for rec in self.filtered(lambda x: x.state == 'draft' and x._is_latam_check_payment()):
            if any(rec.currency_id != check.currency_id for check in rec._get_latam_checks()):
                msgs.append(_('The currency of the payment and the currency of the check must be the same.'))
            if not rec.currency_id.is_zero(sum(rec._get_latam_checks().mapped('amount')) - rec.amount):
                msgs.append(
                    _('The amount of the payment  does not match the amount of the selected check. '
                      'Please try to deselect and select the check again.')
                )
            # checks being moved
            if rec._is_latam_check_payment(check_subtype='move_check'):
                if any(check.payment_id.state == 'draft' for check in rec.l10n_latam_move_check_ids):
                    msgs.append(
                        _('Selected checks "%s" are not posted', rec.l10n_latam_move_check_ids.filtered(lambda x: x.payment_id.state == 'draft').mapped('display_name'))
                    )
                elif rec.payment_type == 'outbound' and any(check.current_journal_id != rec.journal_id for check in rec.l10n_latam_move_check_ids):
                    # check outbound payment and transfer or inbound transfer
                    msgs.append(_(
                        'Some checks are not anymore in journal, it seems it has been moved by another payment.')
                    )
                elif rec.payment_type == 'inbound' and not rec._is_latam_check_transfer() and any(rec.l10n_latam_move_check_ids.mapped('current_journal_id')):
                    msgs.append(
                        _("Some checks are already in hand and can't be received again. Checks: %s",
                          ', '.join(rec.l10n_latam_move_check_ids.mapped('display_name')))
                    )

                for check in rec.l10n_latam_move_check_ids:
                    date = rec.date or fields.Datetime.now()

                    last_operation = check._get_last_operation()
                    if last_operation and last_operation[0].date > date:
                        msgs.append(
                            _(
                              "It seems you're trying to move a check with a date (%(date)s) prior to last "
                              "operation done with the check (%(last_operation)s). This may be wrong, please "
                              "double check it. By continue, the last operation on "
                              "the check will remain being %(last_operation)s",
                              date=format_date(self.env, date), last_operation=last_operation.display_name
                            )
                        )
        return msgs

    def _get_reconciled_checks_error(self):
        checks_reconciled = self.l10n_latam_new_check_ids.filtered(lambda x: x.issue_state in ['debited', 'voided'])
        if checks_reconciled:
            raise UserError(
                _("You can't cancel or re-open a payment with checks if some check has been debited or been voided. "
                  "Checks:\n%s", ('\n'.join(['* %s (%s)' % (x.name, x.issue_state) for x in checks_reconciled])))
            )

    def action_cancel(self):
        self._get_reconciled_checks_error()
        super().action_cancel()

    def action_draft(self):
        self._get_reconciled_checks_error()
        super().action_draft()

    def _l10n_latam_check_split_move(self):
        for payment in self.filtered(lambda x: x.payment_method_code == 'own_checks' and x.payment_type == 'outbound'):
            if len(payment.l10n_latam_new_check_ids) == 1:
                liquidity_line = payment._seek_for_lines()[0]
                payment.l10n_latam_new_check_ids.outstanding_line_id = liquidity_line.id
                continue

            vals = {
                'journal_id': payment.journal_id.id,
                'move_type': 'entry',
                'line_ids': [],
            }
            payment_liquidity_line = payment._seek_for_lines()[0]

            # One line per check
            checks_total = sum(payment.l10n_latam_new_check_ids.mapped('amount'))
            liquidity_balance_total = 0.0
            liquidity_balance = 0.0
            for check in payment.l10n_latam_new_check_ids:
                liquidity_amount_currency = -check.amount

                if check == payment.l10n_latam_new_check_ids[-1]:
                    liquidity_balance = payment.currency_id.round(payment_liquidity_line.balance - liquidity_balance)
                else:
                    liquidity_balance = payment.currency_id.round(payment_liquidity_line.balance * check.amount / checks_total)
                    liquidity_balance_total += liquidity_balance

                vals['line_ids'].append(
                    Command.create({
                        'name': _(
                            'Check %(check_number)s - %(suffix)s',
                            check_number=check.name,
                            suffix=''.join([item[1] for item in payment._get_aml_default_display_name_list()])),
                        'date_maturity': check.payment_date,
                        'amount_currency': liquidity_amount_currency,
                        'currency_id': check.currency_id.id,
                        'debit': max(0.0, liquidity_balance),
                        'credit': -min(liquidity_balance, 0.0),
                        'partner_id': payment_liquidity_line.partner_id.id,
                        'account_id': payment_liquidity_line.account_id.id,
                        'l10n_latam_check_ids': [Command.link(check.id)]
                    }),
                )

            # Cancel payment line
            vals['line_ids'].append(
                Command.create({
                    'name': payment_liquidity_line.name,
                    'date_maturity': payment_liquidity_line.date_maturity,
                    'amount_currency': -payment_liquidity_line.amount_currency,
                    'currency_id': payment_liquidity_line.currency_id.id,
                    'debit': -payment_liquidity_line.debit,
                    'credit': -payment_liquidity_line.credit,
                    'partner_id': payment_liquidity_line.partner_id.id,
                    'account_id': payment_liquidity_line.account_id.id,
                }),
            )
            move_id = self.env['account.move'].create(vals)
            move_id.action_post()
            split_move_counterpart_line = move_id.line_ids.filtered(lambda x: x.amount_currency == -payment_liquidity_line.amount_currency)
            (split_move_counterpart_line + payment_liquidity_line).reconcile()

    def _l10n_latam_check_unlink_split_move(self):
        self.ensure_one()
        for check in self.l10n_latam_new_check_ids:
            if self.move_id == check.outstanding_line_id.move_id:
                check.outstanding_line_id = False
                continue
            check.outstanding_line_id.move_id.button_draft()
            check.outstanding_line_id.move_id.unlink()

    @api.depends(
        'payment_method_line_id', 'state', 'date', 'amount', 'currency_id', 'company_id',
        'l10n_latam_move_check_ids.issuer_vat', 'l10n_latam_move_check_ids.bank_id', 'l10n_latam_move_check_ids.payment_id.date',
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
                        ('payment_id.state', '!=', 'draft'),
                        ('id', '!=', check._origin.id)], limit=1)
                if same_checks:
                    msgs.append(
                        _("Other checks were found with same number, issuer and bank. Please double check you are not "
                          "encoding the same check more than once. List of other payments/checks: %s",
                          ", ".join(same_checks.mapped('display_name')))
                    )
            rec.l10n_latam_check_warning_msg = msgs and '* %s' % '\n* '.join(msgs) or False

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ('l10n_latam_new_check_ids',)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)

        # if only one check we don't create the split line, we add same data on liquidity line
        if self.payment_method_code == 'own_checks' and self.payment_type == 'outbound' and len(self.l10n_latam_new_check_ids) == 1:
            res[0].update({
                'name': _(
                    'Check %(check_number)s - %(suffix)s',
                    check_number=self.l10n_latam_new_check_ids.name,
                    suffix=''.join([item[1] for item in self._get_aml_default_display_name_list()])),
                'date_maturity': self.l10n_latam_new_check_ids.payment_date,
            })
        # we dont check the payment method code because when deposited on bank/cash journals pay method is manual but we still change the label
        # we dont want this names on the own checks because it doesn't add value, already each split/check line will have it name
        elif (self.l10n_latam_new_check_ids or self.l10n_latam_move_check_ids) and self.payment_method_code != 'own_checks':
            check_name = [check_name for check_name in (self.l10n_latam_new_check_ids | self.l10n_latam_move_check_ids).mapped('name') if check_name]
            document_name = (
                _('Checks %s received') if self.payment_type == 'inbound' else _('Checks %s delivered')) % (
                ', '.join(check_name)
            )
            res[0].update({
                'name': document_name + ' - ' + ''.join([item[1] for item in self._get_aml_default_display_name_list()]),
            })
        return res

    @api.depends('l10n_latam_move_check_ids')
    def _compute_destination_account_id(self):
        # EXTENDS 'account'
        super()._compute_destination_account_id()
        for payment in self:
            if payment.l10n_latam_move_check_ids and (not payment.partner_id or payment.partner_id == payment.company_id.partner_id):
                payment.destination_account_id = payment.company_id.transfer_account_id.id

    def _is_latam_check_transfer(self):
        self.ensure_one()
        return not self.partner_id and self.destination_account_id == self.company_id.transfer_account_id
