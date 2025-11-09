from collections import defaultdict

import markupsafe

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import frozendict, SQL


class AccountPaymentRegister(models.TransientModel):
    _name = 'account.payment.register'
    _description = 'Pay'
    _check_company_auto = True

    # == Business fields ==
    payment_date = fields.Date(string="Payment Date", required=True,
        default=fields.Date.context_today)
    amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False,
        compute='_compute_amount')
    hide_writeoff_section = fields.Boolean(compute="_compute_hide_writeoff_section")
    communication = fields.Char(string="Memo", store=True, readonly=False,
        compute='_compute_communication')
    group_payment = fields.Boolean(string="Group Payments", store=True, readonly=False,
        compute='_compute_group_payment',
        help="Only one payment will be created by partner (bank), instead of one per bill.")
    early_payment_discount_mode = fields.Boolean(compute='_compute_early_payment_discount_mode')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id', store=True, readonly=False, precompute=True,
        help="The payment's currency.")
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        check_company=True,
        domain="[('id', 'in', available_journal_ids)]")
    available_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )
    available_partner_bank_ids = fields.Many2many(
        comodel_name='res.partner.bank',
        compute='_compute_available_partner_bank_ids',
    )
    partner_bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string="Recipient Bank Account",
        readonly=False,
        store=True,
        compute='_compute_partner_bank_id',
        domain="[('id', 'in', available_partner_bank_ids)]",
    )
    company_currency_id = fields.Many2one('res.currency', string="Company Currency",
        related='company_id.currency_id')
    qr_code = fields.Html(
        string="QR Code URL",
        compute="_compute_qr_code",
    )

    batches = fields.Binary(compute='_compute_batches', export_string_translation=False)
    installments_mode = fields.Selection(
        selection=[
            ('next', "Next Installment"),
            ('overdue', "Overdue Amount"),
            ('before_date', "Before Next Payment Date"),
            ('full', "Full Amount"),
        ],
        compute='_compute_installments_mode',
        readonly=False,
        store=True,
        export_string_translation=False
    )
    installments_switch_html = fields.Html(
        compute='_compute_installments_switch_values',
    )
    installments_switch_amount = fields.Monetary(
        compute='_compute_installments_switch_values',
        currency_field='currency_id',
    )
    custom_user_amount = fields.Monetary(currency_field='currency_id')
    custom_user_currency_id = fields.Many2one(comodel_name='res.currency')

    # == Fields given through the context ==
    line_ids = fields.Many2many('account.move.line', 'account_payment_register_move_line_rel', 'wizard_id', 'line_id',
        string="Journal items", readonly=True, copy=False,)
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', store=True, copy=False,
        compute='_compute_from_lines')
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], store=True, copy=False,
        compute='_compute_from_lines')
    source_amount = fields.Monetary(
        string="Amount to Pay (company currency)", store=True, copy=False,
        currency_field='company_currency_id',
        compute='_compute_from_lines')
    source_amount_currency = fields.Monetary(
        string="Amount to Pay (foreign currency)", store=True, copy=False,
        currency_field='source_currency_id',
        compute='_compute_from_lines')
    source_currency_id = fields.Many2one('res.currency',
        string='Source Currency', store=True, copy=False,
        compute='_compute_from_lines')
    can_edit_wizard = fields.Boolean(store=True, copy=False,
        compute='_compute_from_lines')  # used to check if user can edit info such as the amount
    can_group_payments = fields.Boolean(store=True, copy=False,
        compute='_compute_can_group_payments')  # can the user see the 'group_payments' box
    company_id = fields.Many2one('res.company', store=True, copy=False,
        compute='_compute_from_lines')
    partner_id = fields.Many2one('res.partner',
        string="Customer/Vendor", store=True, copy=False, ondelete='restrict',
        compute='_compute_from_lines')

    # == Payment methods fields ==
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
        readonly=False, store=True,
        compute='_compute_payment_method_line_id',
        domain="[('id', 'in', available_payment_method_line_ids)]",
        help="Manual: Pay or Get paid by any method outside of Odoo.\n"
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line', compute='_compute_payment_method_line_fields')
    payment_method_code = fields.Char(related='payment_method_line_id.code')

    # == Payment difference fields ==
    payment_difference = fields.Monetary(
        compute='_compute_payment_difference')
    payment_difference_handling = fields.Selection(
        string="Payment Difference Handling",
        selection=[('open', 'Keep open'), ('reconcile', 'Mark as fully paid')],
        compute='_compute_payment_difference_handling',
        store=True,
        readonly=False,
    )
    writeoff_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Difference Account",
        copy=False,
        check_company=True,
    )
    writeoff_label = fields.Char(string='Journal Item Label', default='Write-Off',
        help='Change label of the counterpart that will hold the payment difference')
    writeoff_is_exchange_account = fields.Boolean(
        compute='_compute_writeoff_is_exchange_account',
    )
    show_payment_difference = fields.Boolean(compute='_compute_show_payment_difference')

    # == Display purpose fields ==
    show_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank') # Used to know whether the field `partner_bank_id` should be displayed
    require_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank') # used to know whether the field `partner_bank_id` should be required
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)
    duplicate_payment_ids = fields.Many2many(comodel_name='account.payment', compute='_compute_duplicate_moves')
    is_register_payment_on_draft = fields.Boolean(compute='_compute_is_register_payment_on_draft')
    actionable_errors = fields.Json(compute='_compute_actionable_errors')

    # == trust check ==
    untrusted_bank_ids = fields.Many2many('res.partner.bank', compute='_compute_trust_values')
    total_payments_amount = fields.Integer(compute='_compute_trust_values')
    untrusted_payments_count = fields.Integer(compute='_compute_trust_values')
    missing_account_partners = fields.Many2many('res.partner', compute='_compute_trust_values')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_communication(self, lines):
        ''' Helper to compute the communication based on lines.
        :param lines:           A recordset of the `account.move.line`'s that will be reconciled.
        :return:                A string representing a communication to be set on payment.
        '''
        if len(lines.move_id) == 1:
            move = lines.move_id
            label = move.payment_reference or move.ref or move.name
        elif any(move.is_outbound() for move in lines.move_id):
            # outgoing payments references should use moves references
            labels = {move.payment_reference or move.ref or move.name for move in lines.move_id}
            return ', '.join(sorted(filter(lambda l: l, labels)))
        else:
            label = self.company_id.get_next_batch_payment_communication()
        return label

    @api.model
    def _get_batch_available_journals(self, batch_result):
        """ Helper to compute the available journals based on the batch.

        :param batch_result:    A batch computed by '_compute_batches'.
        :return:                A recordset of account.journal.
        """
        payment_type = batch_result['payment_values']['payment_type']
        company = batch_result['lines'].company_id
        journals = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', ('bank', 'cash', 'credit')),
        ])
        if payment_type == 'inbound':
            return journals.filtered('inbound_payment_method_line_ids')
        else:
            return journals.filtered('outbound_payment_method_line_ids')

    @api.model
    def _get_batch_journal(self, batch_result):
        """ Helper to compute the journal based on the batch.

        :param batch_result:    A batch computed by '_compute_batches'.
        :return:                An account.journal record.
        """
        payment_values = batch_result['payment_values']
        foreign_currency_id = payment_values['currency_id']
        partner_bank_id = payment_values['partner_bank_id']
        company = min(batch_result['lines'].company_id, key=lambda c: len(c.parent_ids))

        currency_domain = [('currency_id', '=', foreign_currency_id)]
        partner_bank_domain = [('bank_account_id', '=', partner_bank_id)]

        default_domain = [
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', ('bank', 'cash', 'credit')),
            ('id', 'in', self.available_journal_ids.ids)
        ]

        if partner_bank_id:
            extra_domains = (
                currency_domain + partner_bank_domain,
                partner_bank_domain,
                currency_domain,
                [],
            )
        else:
            extra_domains = (
                currency_domain,
                [],
            )

        for extra_domain in extra_domains:
            journal = self.env['account.journal'].search(default_domain + extra_domain, limit=1)
            if journal:
                return journal

        return self.env['account.journal']

    @api.model
    def _get_batch_available_partner_banks(self, batch_result, journal):
        payment_values = batch_result['payment_values']

        # A specific bank account is set on the journal. The user must use this one.
        if payment_values['payment_type'] == 'inbound':
            # Receiving money on a bank account linked to the journal.
            return journal.bank_account_id
        else:
            company = min(batch_result['lines'].company_id, key=lambda c: len(c.sudo().parent_ids))
            # Sending money to a bank account owned by a partner.
            return batch_result['lines'].partner_id.bank_ids.filtered(lambda x: x.company_id.id in (False, company.id))._origin

    @api.model
    def _get_line_batch_key(self, line):
        ''' Turn the line passed as parameter to a dictionary defining on which way the lines
        will be grouped together.
        :return: A python dictionary.
        '''
        move = line.move_id

        partner_bank_account = self.env['res.partner.bank']
        if move.is_invoice(include_receipts=True):
            partner_bank_account = move.partner_bank_id._origin

        return {
            'partner_id': line.partner_id.id,
            'account_id': line.account_id.id,
            'currency_id': line.currency_id.id,
            'partner_bank_id': partner_bank_account.id,
            'partner_type': 'customer' if line.account_type == 'asset_receivable' else 'supplier',
        }

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        ''' Extract values from the batch passed as parameter (see '_compute_batches')
        to be mounted in the wizard view.
        :param batch_result:    A batch computed by '_compute_batches'.
        :return:                A dictionary containing valid fields
        '''
        payment_values = batch_result['payment_values']
        lines = batch_result['lines']
        company = min(lines.company_id, key=lambda c: len(c.sudo().parent_ids)) if not self._from_sibling_companies(lines) else lines.company_id.root_id

        source_amount = abs(sum(lines.mapped('amount_residual')))
        if payment_values['currency_id'] == company.currency_id.id:
            source_amount_currency = source_amount
        else:
            source_amount_currency = abs(sum(lines.mapped('amount_residual_currency')))

        return {
            'company_id': company.id,
            'partner_id': payment_values['partner_id'],
            'partner_type': payment_values['partner_type'],
            'payment_type': payment_values['payment_type'],
            'source_currency_id': payment_values['currency_id'],
            'source_amount': source_amount,
            'source_amount_currency': source_amount_currency,
        }

    @api.model
    def _from_sibling_companies(self, lines):
        return len(lines.company_id) > 1 and not any(c.root_id in lines.company_id for c in lines.company_id)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('early_payment_discount_mode', 'can_edit_wizard', 'can_group_payments', 'group_payment', 'payment_method_line_id')
    def _compute_show_payment_difference(self):
        for wizard in self:
            wizard.show_payment_difference = (
                wizard.payment_difference != 0.0
                and not wizard.early_payment_discount_mode
                and wizard.can_edit_wizard
                and (not wizard.can_group_payments or wizard.group_payment)
                and wizard.payment_method_line_id.payment_account_id
            )

    @api.depends('line_ids')
    def _compute_batches(self):
        ''' Group the account.move.line linked to the wizard together.
        Lines are grouped if they share 'partner_id','account_id','currency_id' & 'partner_type' and if
        0 or 1 partner_bank_id can be determined for the group.

        Computes a list of batches, each one containing:
            * payment_values:   A dictionary of payment values.
            * moves:        An account.move recordset.
        '''
        for wizard in self:
            lines = wizard.line_ids._origin

            if len(lines.company_id.root_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different companies."))
            if not lines:
                raise UserError(_("You can't open the register payment wizard without at least one receivable/payable line."))

            batches = defaultdict(lambda: {'lines': self.env['account.move.line']})
            banks_per_partner = defaultdict(lambda: {'inbound': set(), 'outbound': set()})
            for line in lines:
                batch_key = self._get_line_batch_key(line)
                vals = batches[frozendict(batch_key)]
                vals['payment_values'] = batch_key
                vals['lines'] += line
                banks_per_partner[batch_key['partner_id']]['inbound' if line.balance > 0.0 else 'outbound'].add(
                    batch_key['partner_bank_id']
                )

            partner_unique_inbound = {p for p, b in banks_per_partner.items() if len(b['inbound']) == 1}
            partner_unique_outbound = {p for p, b in banks_per_partner.items() if len(b['outbound']) == 1}

            # Compute 'payment_type'.
            batch_vals = []
            seen_keys = set()
            for i, key in enumerate(list(batches)):
                if key in seen_keys:
                    continue
                vals = batches[key]
                lines = vals['lines']
                merge = (
                    batch_key['partner_id'] in partner_unique_inbound
                    and batch_key['partner_id'] in partner_unique_outbound
                )
                if merge:
                    for other_key in list(batches)[i + 1:]:
                        if other_key in seen_keys:
                            continue
                        other_vals = batches[other_key]
                        if all(
                            other_vals['payment_values'][k] == v
                            for k, v in vals['payment_values'].items()
                            if k not in ('partner_bank_id', 'payment_type')
                        ):
                            # add the lines in this batch and mark as seen
                            lines += other_vals['lines']
                            seen_keys.add(other_key)
                balance = sum(lines.mapped('balance'))
                vals['payment_values']['payment_type'] = 'inbound' if balance > 0.0 else 'outbound'
                if merge:
                    partner_banks = banks_per_partner[batch_key['partner_id']]
                    vals['partner_bank_id'] = partner_banks[vals['payment_values']['payment_type']]
                    vals['lines'] = lines
                batch_vals.append(vals)

            wizard.batches = batch_vals

    @api.depends('payment_method_line_id', 'line_ids', 'group_payment', 'partner_bank_id')
    def _compute_trust_values(self):
        for wizard in self:
            total_payment_count = 0
            untrusted_payments_count = 0
            untrusted_accounts = self.env['res.partner.bank']
            missing_account_partners = self.env['res.partner']

            # Validate batches; if require_partner_bank_account and the account isn't setup and trusted, we do not allow the payment
            for batch in wizard.batches:
                payment_count = 1 if wizard.group_payment else len(batch['lines'])
                total_payment_count += payment_count
                # Use the currently selected partner_bank_id if in edit mode, otherwise use batch account
                batch_account = wizard.partner_bank_id or wizard._get_batch_account(batch)
                if wizard.require_partner_bank_account:
                    if not batch_account:
                        missing_account_partners += batch['lines'].partner_id
                    elif not batch_account.allow_out_payment:
                        untrusted_payments_count += payment_count
                        untrusted_accounts |= batch_account

            wizard.update({
                'total_payments_amount': total_payment_count,
                'untrusted_payments_count': untrusted_payments_count,
                'untrusted_bank_ids': untrusted_accounts or False,
                'missing_account_partners': missing_account_partners or False,
            })

    @api.depends('line_ids')
    def _compute_from_lines(self):
        ''' Load initial values from the account.moves passed through the context. '''
        for wizard in self:
            batch_result = wizard.batches[0]
            wizard_values_from_batch = wizard._get_wizard_values_from_batch(batch_result)

            if len(wizard.batches) == 1:
                # == Single batch to be mounted on the view ==
                wizard.update(wizard_values_from_batch)

                wizard.can_edit_wizard = True
            else:
                # == Multiple batches: The wizard is not editable  ==
                lines = sum((batch_result['lines'] for batch_result in wizard.batches), self.env['account.move.line'])
                company = min(lines.company_id, key=lambda c: len(c.parent_ids)) if not self._from_sibling_companies(lines) else lines.company_id.root_id
                wizard.update({
                    'company_id': company.id,
                    'partner_id': False,
                    'partner_type': False,
                    'payment_type': wizard_values_from_batch['payment_type'],
                    'source_currency_id': False,
                    'source_amount': False,
                    'source_amount_currency': False,
                })

                wizard.can_edit_wizard = False

    @api.depends('batches', 'amount')
    def _compute_can_group_payments(self):
        for wizard in self:
            if len(wizard.batches) == 1:
                lines = wizard.batches[0]['lines']
                wizard.can_group_payments = (
                    len(lines) != 1
                    and not (len(lines.move_id) == 1 and lines.move_id.is_invoice(include_receipts=True))
                )
            else:
                wizard.can_group_payments = any(len(batch_result['lines']) != 1 for batch_result in wizard.batches)

    @api.depends('can_edit_wizard', 'amount')
    def _compute_communication(self):
        # The communication can't be computed in '_compute_from_lines' because
        # it's a compute editable field and then, should be computed in a separated method.
        for wizard in self:
            if wizard.can_edit_wizard and wizard.installments_mode == 'full' or wizard.custom_user_amount:
                lines = wizard.line_ids
            else:
                lines = wizard._get_total_amounts_to_pay(wizard.batches)['lines']
            wizard.communication = wizard._get_communication(lines)

    @api.depends('can_edit_wizard')
    def _compute_group_payment(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.group_payment = len(wizard.batches[0]['lines'].move_id) == 1
            else:
                wizard.group_payment = False

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id or wizard.source_currency_id or wizard.company_id.currency_id

    @api.depends('payment_type', 'company_id', 'can_edit_wizard')
    def _compute_available_journal_ids(self):
        for wizard in self:
            available_journals = self.env['account.journal']
            for batch in wizard.batches:
                available_journals |= wizard._get_batch_available_journals(batch)
            wizard.available_journal_ids = [Command.set(available_journals.ids)]

    @api.depends('available_journal_ids')
    def _compute_journal_id(self):
        for wizard in self:
            if wizard.journal_id in wizard.available_journal_ids:
                continue
            move_payment_method_lines = wizard.line_ids.move_id.preferred_payment_method_line_id
            if move_payment_method_lines and len(move_payment_method_lines) == 1:
                wizard.journal_id = move_payment_method_lines.journal_id
            elif wizard.can_edit_wizard:
                batch = wizard.batches[0]
                wizard.journal_id = wizard._get_batch_journal(batch)
            else:
                wizard.journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(wizard.company_id),
                    ('type', 'in', ('bank', 'cash', 'credit')),
                    ('id', 'in', self.available_journal_ids.ids)
                ], limit=1)

    @api.depends('can_edit_wizard', 'journal_id')
    def _compute_available_partner_bank_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard.batches[0]
                wizard.available_partner_bank_ids = wizard._get_batch_available_partner_banks(batch, wizard.journal_id)
            else:
                wizard.available_partner_bank_ids = None

    @api.depends('journal_id', 'available_partner_bank_ids')
    def _compute_partner_bank_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard.batches[0]
                partner_bank_id = batch['payment_values']['partner_bank_id']
                available_partner_banks = wizard.available_partner_bank_ids._origin
                if partner_bank_id and partner_bank_id in available_partner_banks.ids:
                    wizard.partner_bank_id = self.env['res.partner.bank'].browse(partner_bank_id)
                else:
                    wizard.partner_bank_id = available_partner_banks[:1]
            else:
                wizard.partner_bank_id = None

    @api.depends('payment_type', 'journal_id', 'currency_id')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines(wizard.payment_type)
            else:
                wizard.available_payment_method_line_ids = False

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        for wizard in self:
            if wizard.journal_id:
                available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines(wizard.payment_type)
            else:
                available_payment_method_lines = False

            if available_payment_method_lines and wizard.payment_method_line_id in available_payment_method_lines:
                continue

            # Select the first available one by default.
            if available_payment_method_lines:
                move_payment_method_lines = wizard.line_ids.move_id.preferred_payment_method_line_id
                if len(move_payment_method_lines) == 1 and move_payment_method_lines.id in available_payment_method_lines.ids:
                    wizard.payment_method_line_id = move_payment_method_lines
                else:
                    wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    @api.depends('payment_method_line_id')
    def _compute_show_require_partner_bank(self):
        """ Computes if the destination bank account must be displayed in the payment form view. By default, it
        won't be displayed but some modules might change that, depending on the payment type."""
        for wizard in self:
            if wizard.journal_id.type == 'cash':
                wizard.show_partner_bank_account = False
            else:
                wizard.show_partner_bank_account = wizard.payment_method_line_id.code in self.env['account.payment']._get_method_codes_using_bank_account()
            wizard.require_partner_bank_account = wizard.payment_method_line_id.code in self.env['account.payment']._get_method_codes_needing_bank_account()

    @api.depends('line_ids')
    def _compute_actionable_errors(self):
        for wizard in self:
            actionable_errors = {}
            if unpaid_matched_payments := wizard.line_ids.move_id.reconciled_payment_ids.filtered(lambda p: p.state == 'in_process'):
                actionable_errors['unpaid_matched_payments'] = {
                    'message': self.env._("There are payments in progress. Make sure you don't pay twice."),
                    'action_text': self.env._("Check them"),
                    'action': unpaid_matched_payments._get_records_action(name=self.env._("Payments")),
                    'level': 'danger',
                }
            wizard.actionable_errors = actionable_errors

    def _convert_to_wizard_currency(self, installments):
        self.ensure_one()
        total_per_currency = defaultdict(lambda: {
            'amount_residual': 0.0,
            'amount_residual_currency': 0.0,
        })
        for installment in installments:
            line = installment['line']
            total_per_currency[line.currency_id]['amount_residual'] += installment['amount_residual']
            total_per_currency[line.currency_id]['amount_residual_currency'] += installment['amount_residual_currency']

        total_amount = 0.0
        wizard_curr = self.currency_id
        comp_curr = self.company_currency_id
        for currency, amounts in total_per_currency.items():
            amount_residual = amounts['amount_residual']
            amount_residual_currency = amounts['amount_residual_currency']
            if currency == wizard_curr:
                # Same currency
                total_amount += amount_residual_currency
            elif currency != comp_curr and wizard_curr == comp_curr:
                # Foreign currency on source line but the company currency one on the opposite line.
                total_amount += currency._convert(amount_residual_currency, comp_curr, self.company_id, self.payment_date)
            elif currency == comp_curr and wizard_curr != comp_curr:
                # Company currency on source line but a foreign currency one on the opposite line.
                total_amount += comp_curr._convert(amount_residual, wizard_curr, self.company_id, self.payment_date)
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                total_amount += comp_curr._convert(amount_residual, wizard_curr, self.company_id, self.payment_date)
        return total_amount

    def _get_total_amounts_to_pay(self, batch_results):
        self.ensure_one()
        next_payment_date = self._get_next_payment_date_in_context()
        amount_per_line_common = []
        amount_per_line_by_default = []
        amount_per_line_full_amount = []
        amount_per_line_for_difference = []
        epd_applied = False
        first_installment_mode = False
        all_lines = self.env['account.move.line']
        for batch_result in batch_results:
            all_lines |= batch_result['lines']
        all_lines = all_lines.sorted(key=lambda line: (line.move_id, line.date_maturity))
        for lines in all_lines.grouped('move_id').values():
            installments = lines._get_installments_data(payment_currency=self.currency_id, payment_date=self.payment_date, next_payment_date=next_payment_date)
            last_installment_mode = False
            for installment in installments:
                line = installment['line']
                if installment['type'] == 'early_payment_discount':
                    epd_applied = True
                    amount_per_line_by_default.append(installment)
                    amount_per_line_for_difference.append({
                        **installment,
                        'amount_residual_currency': line.amount_residual_currency,
                        'amount_residual': line.amount_residual,
                    })
                    continue

                # Installments.
                # In case of overdue, all of them are sum as a default amount to be paid.
                # The next installment is added for the difference.
                if (
                    line.display_type == 'payment_term'
                    and installment['type'] in ('overdue', 'next', 'before_date')
                ):
                    if installment['type'] == 'overdue':
                        amount_per_line_common.append(installment)
                    elif installment['type'] == 'before_date':
                        amount_per_line_common.append(installment)
                        first_installment_mode = 'before_date'
                    elif installment['type'] == 'next':
                        if last_installment_mode in ('next', 'overdue', 'before_date'):
                            amount_per_line_full_amount.append(installment)
                        elif not last_installment_mode:
                            amount_per_line_common.append(installment)
                            # if we have several moves and one of them has as first installment, a 'next', we want
                            # the whole batches to have a mode of 'next', overriding an 'overdue' on another move
                            first_installment_mode = 'next'
                    last_installment_mode = installment['type']
                    first_installment_mode = first_installment_mode or last_installment_mode
                    continue

                amount_per_line_common.append(installment)

        common = self._convert_to_wizard_currency(amount_per_line_common)
        by_default = self._convert_to_wizard_currency(amount_per_line_by_default)
        for_difference = self._convert_to_wizard_currency(amount_per_line_for_difference)
        full_amount = self._convert_to_wizard_currency(amount_per_line_full_amount)

        lines = self.env['account.move.line']
        for value in amount_per_line_common + amount_per_line_by_default:
            lines |= value['line']

        return {
            # default amount shown in the wizard (different from full for installments)
            'amount_by_default': abs(common + by_default),
            'full_amount': abs(common + by_default + full_amount),
            # for_difference is used to compute the difference for the Early Payment Discount
            'amount_for_difference': abs(common + for_difference),
            'full_amount_for_difference': abs(common + for_difference + full_amount),
            'epd_applied': epd_applied,
            'installment_mode': first_installment_mode,
            'lines': lines,
        }

    @api.onchange('amount')
    def _onchange_amount(self):
        if not self.can_edit_wizard or not self.currency_id:
            return

        total_amount_values = self._get_total_amounts_to_pay(self.batches)
        is_custom_user_amount = all(
            not self.currency_id.is_zero(self.amount - total_amount_values[amount_field])
            for amount_field in ('amount_by_default', 'amount_for_difference', 'full_amount', 'full_amount_for_difference')
        )
        if is_custom_user_amount:
            self.custom_user_amount = self.amount
            self.custom_user_currency_id = self.currency_id
        else:
            self.custom_user_amount = None
            self.custom_user_currency_id = None

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if not self.can_edit_wizard or not self.currency_id or not self.payment_date or not self.custom_user_amount:
            return

        if self.custom_user_amount:
            self.custom_user_amount = self.amount = self.custom_user_currency_id._convert(
                from_amount=self.custom_user_amount,
                to_currency=self.currency_id,
                date=self.payment_date,
                company=self.company_id,
            )

    @api.onchange('payment_date')
    def _onchange_payment_date(self):
        if not self.can_edit_wizard or not self.currency_id or not self.payment_date or not self.custom_user_amount:
            return

        self.amount = self.custom_user_amount

    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date', 'installments_mode')
    def _compute_amount(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id or not wizard.payment_date or wizard.custom_user_amount:
                wizard.amount = wizard.amount
            else:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                wizard.amount = total_amount_values['amount_by_default']

    @api.depends('amount')
    def _compute_installments_mode(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id:
                wizard.installments_mode = wizard.installments_mode
            else:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                if wizard.currency_id.compare_amounts(wizard.amount, total_amount_values['full_amount']) == 0:
                    wizard.installments_mode = 'full'
                elif wizard.currency_id.compare_amounts(wizard.amount, total_amount_values['amount_by_default']) == 0:
                    wizard.installments_mode = total_amount_values['installment_mode']
                else:
                    wizard.installments_mode = 'full'

    @api.depends('installments_mode')
    def _compute_installments_switch_values(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id:
                wizard.installments_switch_amount = wizard.installments_switch_amount
                wizard.installments_switch_html = wizard.installments_switch_html
            else:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                html_lines = []
                if wizard.installments_mode == 'full':
                    is_full_match = (
                        wizard.currency_id.is_zero(total_amount_values['full_amount'] - wizard.amount)
                        and wizard.currency_id.is_zero(total_amount_values['full_amount'] - total_amount_values['amount_by_default'])
                    )
                    wizard.installments_switch_amount = 0.0 if is_full_match else total_amount_values['amount_by_default']
                    if not is_full_match and not wizard.currency_id.is_zero(wizard.amount):
                        switch_message = (
                            _("Consider paying the amount with %(btn_start)searly payment discount%(btn_end)s instead.")
                            if total_amount_values['epd_applied']
                            else _("Consider paying in %(btn_start)sinstallments%(btn_end)s instead.")
                        )
                        html_lines += [
                            _("This is the full amount."),
                            switch_message,
                        ]
                elif wizard.installments_mode == 'overdue':
                    wizard.installments_switch_amount = total_amount_values['full_amount']
                    html_lines += [
                        _("This is the overdue amount."),
                        _("Consider paying the %(btn_start)sfull amount%(btn_end)s."),
                    ]
                elif wizard.installments_mode == 'before_date':
                    wizard.installments_switch_amount = total_amount_values['full_amount']
                    next_payment_date = self._get_next_payment_date_in_context()
                    html_lines += [
                        _("Total for the installments before %(date)s.", date=(next_payment_date or fields.Date.context_today(self))),
                        _("Consider paying the %(btn_start)sfull amount%(btn_end)s."),
                    ]
                elif wizard.installments_mode == 'next':
                    wizard.installments_switch_amount = total_amount_values['full_amount']
                    html_lines += [
                        _("This is the next unreconciled installment."),
                        _("Consider paying the %(btn_start)sfull amount%(btn_end)s."),
                    ]
                else:
                    wizard.installments_switch_amount = wizard.installments_switch_amount

                if wizard.custom_user_amount:
                    wizard.installments_switch_html = None
                else:
                    wizard.installments_switch_html = markupsafe.Markup('<br/>').join(html_lines) % {
                        'btn_start': markupsafe.Markup('<span class="installments_switch_button btn btn-link p-0 align-baseline">'),
                        'btn_end': markupsafe.Markup('</span>'),
                    }

    @api.depends('can_edit_wizard', 'payment_date', 'currency_id', 'amount')
    def _compute_early_payment_discount_mode(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id or not wizard.payment_date:
                wizard.early_payment_discount_mode = wizard.early_payment_discount_mode
            else:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                wizard.early_payment_discount_mode = (
                    total_amount_values['epd_applied']
                    and (
                        wizard.currency_id.compare_amounts(wizard.amount, total_amount_values['amount_by_default']) == 0
                        or wizard.currency_id.compare_amounts(wizard.amount, total_amount_values['full_amount']) == 0
                    )
                )

    @api.depends('can_edit_wizard', 'amount', 'installments_mode')
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.payment_date:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                if wizard.installments_mode in ('overdue', 'next', 'before_date'):
                    wizard.payment_difference = total_amount_values['amount_for_difference'] - wizard.amount
                elif wizard.installments_mode == 'full':
                    wizard.payment_difference = total_amount_values['full_amount_for_difference'] - wizard.amount
                else:
                    wizard.payment_difference = total_amount_values['amount_for_difference'] - wizard.amount
            else:
                wizard.payment_difference = 0.0

    @api.depends('can_edit_wizard', 'writeoff_account_id')
    def _compute_writeoff_is_exchange_account(self):
        for wizard in self:
            wizard.writeoff_is_exchange_account = all((
                wizard.can_edit_wizard,
                wizard.currency_id != wizard.source_currency_id,
                wizard.writeoff_account_id,
                wizard.writeoff_account_id in (
                    wizard.company_id.expense_currency_exchange_account_id,
                    wizard.company_id.income_currency_exchange_account_id,
                ),
            ))

    @api.depends('early_payment_discount_mode')
    def _compute_payment_difference_handling(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.payment_difference_handling = 'reconcile' if wizard.early_payment_discount_mode else 'open'
            else:
                wizard.payment_difference_handling = False

    @api.depends('early_payment_discount_mode')
    def _compute_hide_writeoff_section(self):
        for wizard in self:
            wizard.hide_writeoff_section = wizard.early_payment_discount_mode

    @api.depends('partner_bank_id', 'amount', 'currency_id', 'payment_method_line_id', 'payment_type', 'communication')
    def _compute_qr_code(self):
        for pay in self:
            qr_html = False
            if pay.partner_bank_id \
               and pay.partner_bank_id.allow_out_payment \
               and pay.payment_method_line_id.code == 'manual' \
               and pay.payment_type == 'outbound' \
               and pay.amount \
               and pay.currency_id:
                b64_qr = pay.partner_bank_id.build_qr_code_base64(
                    amount=pay.amount,
                    free_communication=pay.communication,
                    structured_communication=pay.communication,
                    currency=pay.currency_id,
                    debtor_partner=pay.partner_id,
                )
                if b64_qr:
                    qr_html = f'''
                        <img class="border border-dark rounded" src="{b64_qr}"/>
                        <br/>
                        <strong>{_('Scan me with your banking app.')}</strong>
                    '''
            pay.qr_code = qr_html

    @api.depends('partner_id', 'amount', 'payment_date', 'payment_type', 'line_ids')
    def _compute_duplicate_moves(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.duplicate_payment_ids = self._fetch_duplicate_reference().get(0, self.env['account.payment'])
            else:
                wizard.duplicate_payment_ids = self.env['account.payment']

    @api.depends('line_ids')
    def _compute_is_register_payment_on_draft(self):
        for wizard in self:
            wizard.is_register_payment_on_draft = any(l.parent_state == 'draft' for l in wizard.line_ids)

    def _fetch_duplicate_reference(self, matching_states=('draft', 'posted')):
        """ Retrieve move ids for possible duplicates of payments. Duplicates moves:
        - Have the same partner_id, amount and date as the payment
        - Are not reconciled
        - Represent a credit in the same account receivable or a debit in the same account payable as the payment, or
        - Represent a credit in outstanding receipts or debit in outstanding payments, so bank statement lines with an
         outstanding counterpart can be matched, or
        - Are in the suspense account
        """
        dummy = self.env['account.payment'].new({
            "company_id": self.company_id,
            "partner_id": self.partner_id,
            "date": self.payment_date,
            "amount": self.amount,
            "payment_type": self.payment_type,
        })
        return dummy._fetch_duplicate_reference(matching_states)
    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields):
        # OVERRIDE
        res = super().default_get(fields)

        if 'line_ids' in fields and 'line_ids' not in res:

            # Retrieve moves to pay from the context.

            if self.env.context.get('active_model') == 'account.move':
                lines = self.env['account.move'].browse(self.env.context.get('active_ids', [])).line_ids
            elif self.env.context.get('active_model') == 'account.move.line':
                lines = self.env['account.move.line'].browse(self.env.context.get('active_ids', []))
            else:
                raise UserError(_(
                    "The register payment wizard should only be called on account.move or account.move.line records."
                ))

            if 'journal_id' in res and not self.env['account.journal'].browse(res['journal_id']).filtered_domain([
                *self.env['account.journal']._check_company_domain(lines.company_id),
                ('type', 'in', ('bank', 'cash', 'credit')),
            ]):
                # default can be inherited from the list view, should be computed instead
                del res['journal_id']

            # Keep lines having a residual amount to pay.
            available_lines = self.env['account.move.line']
            valid_account_types = self.env['account.payment']._get_valid_payment_account_types()
            for line in lines:

                if line.account_type not in valid_account_types:
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                else:
                    if line.company_currency_id.is_zero(line.amount_residual):
                        continue
                available_lines |= line

            # Check.
            if not available_lines:
                raise UserError(_("There's nothing left to pay for the selected journal items, so no payment registration is necessary. You've got your finances under control like a boss!"))
            if len(lines.company_id.root_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different companies."))
            if self._from_sibling_companies(lines) and lines.company_id.root_id not in self.env.user.company_ids:
                raise UserError(_("You can't create payments for entries belonging to different branches without access to parent company."))
            if len(set(available_lines.mapped('account_type'))) > 1:
                raise UserError(_("You can't register payments for both inbound and outbound moves at the same time."))

            res['line_ids'] = [(6, 0, available_lines.ids)]

        return res

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'memo': self.communication,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'write_off_line_vals': [],
        }

        if self.payment_difference_handling == 'reconcile':
            if self.early_payment_discount_mode:
                epd_aml_values_list = []
                for aml in batch_result['lines']:
                    if aml.move_id._is_eligible_for_early_payment_discount(self.currency_id, self.payment_date):
                        epd_aml_values_list.append({
                            'aml': aml,
                            'amount_currency': -aml.amount_residual_currency,
                            'balance': aml.currency_id._convert(-aml.amount_residual_currency, aml.company_currency_id, date=self.payment_date),
                        })

                open_amount_currency = self.payment_difference * (-1 if self.payment_type == 'outbound' else 1)
                open_balance = self.currency_id._convert(open_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date)
                early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
                for aml_values_list in early_payment_values.values():
                    payment_vals['write_off_line_vals'] += aml_values_list

            elif not self.currency_id.is_zero(self.payment_difference):

                if self.writeoff_is_exchange_account:
                    # Force the rate when computing the 'balance' only when the payment has a foreign currency.
                    # If not, the rate is forced during the reconciliation to put the difference directly on the
                    # exchange difference.
                    if self.currency_id != self.company_currency_id:
                        payment_vals['force_balance'] = sum(batch_result['lines'].mapped('amount_residual'))
                else:
                    if self.payment_type == 'inbound':
                        # Receive money.
                        write_off_amount_currency = self.payment_difference
                    else:  # if self.payment_type == 'outbound':
                        # Send money.
                        write_off_amount_currency = -self.payment_difference

                    payment_vals['write_off_line_vals'].append({
                        'name': self.writeoff_label,
                        'account_id': self.writeoff_account_id.id,
                        'partner_id': self.partner_id.id,
                        'currency_id': self.currency_id.id,
                        'amount_currency': write_off_amount_currency,
                        'balance': self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date),
                    })

        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        batch_values = self._get_wizard_values_from_batch(batch_result)

        if batch_values['payment_type'] == 'inbound':
            partner_bank_id = self.journal_id.bank_account_id.id
        else:
            partner_bank_id = batch_result['payment_values']['partner_bank_id']

        payment_method_line = self.payment_method_line_id

        if batch_values['payment_type'] != payment_method_line.payment_type:
            payment_method_line = self.journal_id._get_available_payment_method_lines(batch_values['payment_type'])[:1]

        payment_vals = {
            'date': self.payment_date,
            'amount': batch_values['source_amount_currency'],
            'payment_type': batch_values['payment_type'],
            'partner_type': batch_values['partner_type'],
            'memo': self._get_communication(batch_result['lines']),
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': batch_values['source_currency_id'],
            'partner_id': batch_values['partner_id'],
            'payment_method_line_id': payment_method_line.id,
            'destination_account_id': batch_result['lines'][0].account_id.id,
            'write_off_line_vals': [],
        }

        # In case it is false, we don't add it to the create vals so that
        # _compute_partner_bank_id is executed at payment creation
        if partner_bank_id:
            payment_vals['partner_bank_id'] = partner_bank_id

        total_amount_values = self._get_total_amounts_to_pay([batch_result])
        total_amount = total_amount_values['amount_by_default']
        currency = self.env['res.currency'].browse(batch_values['source_currency_id'])
        if total_amount_values['epd_applied']:
            payment_vals['amount'] = total_amount

            epd_aml_values_list = []
            for aml in batch_result['lines']:
                if aml.move_id._is_eligible_for_early_payment_discount(currency, self.payment_date):
                    epd_aml_values_list.append({
                        'aml': aml,
                        'amount_currency': -aml.amount_residual_currency,
                        'balance': currency._convert(-aml.amount_residual_currency, aml.company_currency_id, self.company_id, self.payment_date),
                    })

            open_amount_currency = (batch_values['source_amount_currency'] - total_amount) * (-1 if batch_values['payment_type'] == 'outbound' else 1)
            open_balance = currency._convert(open_amount_currency, aml.company_currency_id, self.company_id, self.payment_date)
            early_payment_values = self.env['account.move']\
                ._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
            for aml_values_list in early_payment_values.values():
                payment_vals['write_off_line_vals'] += aml_values_list

        return payment_vals

    def _init_payments(self, to_process, edit_mode=False):
        """ Create the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_compute_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """

        payments = self.env['account.payment']\
            .with_context(skip_invoice_sync=True)\
            .create([x['create_vals'] for x in to_process])

        for payment, vals in zip(payments, to_process):
            vals['payment'] = payment

            # If payments are made using a currency different than the source one, ensure the balance match exactly in
            # order to fully paid the source journal items.
            # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
            # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
            if edit_mode and payment.move_id:
                lines = vals['to_reconcile']

                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    if liquidity_lines[0].balance:
                        payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    else:
                        payment_rate = 0.0
                    source_balance_converted = abs(source_balance) * payment_rate

                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    if debit_lines and credit_lines:
                        payment.move_id.write({'line_ids': [
                            (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                            (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                        ]})
        return payments

    def _post_payments(self, to_process, edit_mode=False):
        """ Post the newly created payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_compute_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        payments = self.env['account.payment']
        for vals in to_process:
            payments |= vals['payment']
        payments.with_context(skip_sale_auto_invoice_send=True).action_post()

    def _reconcile_payments(self, to_process, edit_mode=False):
        """ Reconcile the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_compute_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', self.env['account.payment']._get_valid_payment_account_types()),
            ('reconciled', '=', False),
        ]
        for vals in to_process:
            payment = vals['payment']
            payment_lines = payment.move_id.line_ids.filtered_domain(domain)
            lines = vals['to_reconcile']
            extra_context = {'forced_rate_from_register_payment': vals['rate']} if 'rate' in vals else {}

            for account in payment_lines.account_id:
                (payment_lines + lines)\
                    .with_context(**extra_context)\
                    .filtered_domain([
                        ('account_id', '=', account.id),
                        ('reconciled', '=', False),
                    ])\
                    .reconcile()
            lines.move_id.matched_payment_ids += payment

    def _create_payments(self):
        self.ensure_one()
        batches = []
        # Skip batches that are not valid (bank account not setup or not trusted but required)
        for batch in self.batches:
            batch_account = self._get_batch_account(batch)
            if self.require_partner_bank_account and (not batch_account or not batch_account.allow_out_payment):
                continue
            batches.append(batch)

        if not batches:
            raise UserError(_(
                "To record payments with %(payment_method)s, the recipient bank account must be manually validated. You should go on the partner bank account in order to validate it.",
                payment_method=self.payment_method_line_id.name,
            ))

        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
            to_process_values = {
                'create_vals': payment_vals,
                'to_reconcile': first_batch_result['lines'],
                'batch': first_batch_result,
            }

            # Force the rate during the reconciliation to put the difference directly on the
            # exchange difference.
            if self.writeoff_is_exchange_account and self.currency_id == self.company_currency_id:
                total_batch_residual = sum(first_batch_result['lines'].mapped('amount_residual_currency'))
                to_process_values['rate'] = abs(total_batch_residual / self.amount) if self.amount else 0.0

            to_process.append(to_process_values)
        else:
            if not self.group_payment:
                # Don't group payments: Create one batch per move.
                lines_to_pay = self._get_total_amounts_to_pay(batches)['lines'] if self.installments_mode in ('next', 'overdue', 'before_date') else self.line_ids
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        if line not in lines_to_pay:
                            continue
                        new_batches.append({
                            **batch_result,
                            'payment_values': {
                                **batch_result['payment_values'],
                                'payment_type': 'inbound' if line.balance > 0 else 'outbound'
                            },
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        lines = sum((batch_result['lines'] for batch_result in batches), self.env['account.move.line'])
        from_sibling_companies = self._from_sibling_companies(lines)
        if from_sibling_companies and lines.company_id.root_id not in self.env.companies:
            # Payment made for sibling companies, we don't want to redirect to the payments
            # to avoid access error, as it will be created as parent company.
            self.env(context={**self.env.context, "dont_redirect_to_payments": True})

        wizard = self.sudo() if from_sibling_companies else self

        payments = wizard._init_payments(to_process, edit_mode=edit_mode)
        wizard._post_payments(to_process, edit_mode=edit_mode)
        wizard._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments.sudo(flag=False)

    def _get_next_payment_date_in_context(self):
        if active_domain := self.env.context.get('active_domain'):
            for domain_elem in active_domain:
                if isinstance(domain_elem, (list, tuple)) and domain_elem[0] == 'next_payment_date' and len(domain_elem) == 3 and isinstance(domain_elem[2], str):
                    return fields.Date.to_date(domain_elem[2])
        return False

    def action_create_payments(self):
        if self.is_register_payment_on_draft:
            self.payment_difference_handling = 'open'
        payments = self._create_payments()

        if self.env.context.get('dont_redirect_to_payments'):
            return True

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

    def _get_batch_account(self, batch_result):
        # Get the batch bank account
        partner_bank_id = batch_result['payment_values']['partner_bank_id']
        available_partner_banks = self._get_batch_available_partner_banks(batch_result, self.journal_id)
        if partner_bank_id and partner_bank_id in available_partner_banks.ids:
            return self.env['res.partner.bank'].browse(partner_bank_id)
        else:
            return available_partner_banks[:1]

    def action_open_untrusted_bank_accounts(self):
        self.ensure_one()
        if len(self.untrusted_bank_ids) == 1:
            action = {
                "view_mode": "form",
                "res_model": "res.partner.bank",
                "type": "ir.actions.act_window",
                "res_id": self.untrusted_bank_ids.id,
                "views": [[self.env.ref("account.view_partner_bank_form_inherit_account").id, "form"]],
            }
        else:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "res.partner.bank",
                "views": [[False, "list"], [self.env.ref("account.view_partner_bank_form_inherit_account").id, "form"]],
                "domain": [["id", "in", self.untrusted_bank_ids.ids]],
            }

        return action

    def action_open_missing_account_partners(self):
        self.ensure_one()
        vals = {}
        if len(self.missing_account_partners) > 1:
            listview_id = self.env.ref('account.partner_missing_account_list_view').id
            vals['views'] = [(listview_id, 'list'), (False, "form")]
        return self.missing_account_partners._get_records_action(**vals)
