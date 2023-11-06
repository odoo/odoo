# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import frozendict


class AccountPaymentRegister(models.TransientModel):
    _name = 'account.payment.register'
    _description = 'Register Payment'

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
        compute='_compute_from_lines') # used to check if user can edit info such as the amount
    can_group_payments = fields.Boolean(store=True, copy=False,
        compute='_compute_from_lines') # can the user see the 'group_payments' box
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
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        compute='_compute_writeoff_account_id',
        store=True,
        readonly=False,
    )
    writeoff_label = fields.Char(string='Journal Item Label', default='Write-Off',
        help='Change label of the counterpart that will hold the payment difference')

    # == Display purpose fields ==
    show_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank') # Used to know whether the field `partner_bank_id` should be displayed
    require_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank') # used to know whether the field `partner_bank_id` should be required
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_batch_communication(self, batch_result):
        ''' Helper to compute the communication based on the batch.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A string representing a communication to be set on payment.
        '''
        labels = set(line.name or line.move_id.ref or line.move_id.name for line in batch_result['lines'])
        return ' '.join(sorted(labels))

    @api.model
    def _get_batch_available_journals(self, batch_result):
        """ Helper to compute the available journals based on the batch.

        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A recordset of account.journal.
        """
        payment_type = batch_result['payment_values']['payment_type']
        company = batch_result['lines'].company_id
        journals = self.env['account.journal'].search([('company_id', '=', company.id), ('type', 'in', ('bank', 'cash'))])
        if payment_type == 'inbound':
            return journals.filtered('inbound_payment_method_line_ids')
        else:
            return journals.filtered('outbound_payment_method_line_ids')

    @api.model
    def _get_batch_journal(self, batch_result):
        """ Helper to compute the journal based on the batch.

        :param batch_result:    A batch returned by '_get_batches'.
        :return:                An account.journal record.
        """
        payment_values = batch_result['payment_values']
        foreign_currency_id = payment_values['currency_id']
        partner_bank_id = payment_values['partner_bank_id']

        currency_domain = [('currency_id', '=', foreign_currency_id)]
        partner_bank_domain = [('bank_account_id', '=', partner_bank_id)]

        default_domain = [
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', batch_result['lines'].company_id.id),
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
        company = batch_result['lines'].company_id

        # A specific bank account is set on the journal. The user must use this one.
        if payment_values['payment_type'] == 'inbound':
            # Receiving money on a bank account linked to the journal.
            return journal.bank_account_id
        else:
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

    def _get_batches(self):
        ''' Group the account.move.line linked to the wizard together.
        Lines are grouped if they share 'partner_id','account_id','currency_id' & 'partner_type' and if
        0 or 1 partner_bank_id can be determined for the group.
        :return: A list of batches, each one containing:
            * payment_values:   A dictionary of payment values.
            * moves:        An account.move recordset.
        '''
        self.ensure_one()

        lines = self.line_ids._origin

        if len(lines.company_id) > 1:
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
                for other_key in list(batches)[i+1:]:
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
        return batch_vals

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        ''' Extract values from the batch passed as parameter (see '_get_batches')
        to be mounted in the wizard view.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A dictionary containing valid fields
        '''
        payment_values = batch_result['payment_values']
        lines = batch_result['lines']
        company = lines[0].company_id

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

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('line_ids')
    def _compute_from_lines(self):
        ''' Load initial values from the account.moves passed through the context. '''
        for wizard in self:
            batches = wizard._get_batches()
            batch_result = batches[0]
            wizard_values_from_batch = wizard._get_wizard_values_from_batch(batch_result)

            if len(batches) == 1:
                # == Single batch to be mounted on the view ==
                wizard.update(wizard_values_from_batch)

                wizard.can_edit_wizard = True
                wizard.can_group_payments = len(batch_result['lines']) != 1
            else:
                # == Multiple batches: The wizard is not editable  ==
                wizard.update({
                    'company_id': batches[0]['lines'][0].company_id.id,
                    'partner_id': False,
                    'partner_type': False,
                    'payment_type': wizard_values_from_batch['payment_type'],
                    'source_currency_id': False,
                    'source_amount': False,
                    'source_amount_currency': False,
                })

                wizard.can_edit_wizard = False
                wizard.can_group_payments = any(len(batch_result['lines']) != 1 for batch_result in batches)

    @api.depends('can_edit_wizard')
    def _compute_communication(self):
        # The communication can't be computed in '_compute_from_lines' because
        # it's a compute editable field and then, should be computed in a separated method.
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.communication = wizard._get_batch_communication(batches[0])
            else:
                wizard.communication = False

    @api.depends('can_edit_wizard')
    def _compute_group_payment(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.group_payment = len(batches[0]['lines'].move_id) == 1
            else:
                wizard.group_payment = False

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id or wizard.source_currency_id or wizard.company_id.currency_id

    @api.depends('payment_type', 'company_id', 'can_edit_wizard')
    def _compute_available_journal_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
                wizard.available_journal_ids = wizard._get_batch_available_journals(batch)
            else:
                wizard.available_journal_ids = self.env['account.journal'].search([
                    ('company_id', '=', wizard.company_id.id),
                    ('type', 'in', ('bank', 'cash')),
                ])

    @api.depends('available_journal_ids')
    def _compute_journal_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
                wizard.journal_id = wizard._get_batch_journal(batch)
            else:
                wizard.journal_id = self.env['account.journal'].search([
                    ('type', 'in', ('bank', 'cash')),
                    ('company_id', '=', wizard.company_id.id),
                    ('id', 'in', self.available_journal_ids.ids)
                ], limit=1)

    @api.depends('can_edit_wizard', 'journal_id')
    def _compute_available_partner_bank_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
                wizard.available_partner_bank_ids = wizard._get_batch_available_partner_banks(batch, wizard.journal_id)
            else:
                wizard.available_partner_bank_ids = None

    @api.depends('journal_id', 'available_partner_bank_ids')
    def _compute_partner_bank_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
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

            # Select the first available one by default.
            if available_payment_method_lines:
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

    def _get_total_amount_using_same_currency(self, batch_result, early_payment_discount=True):
        self.ensure_one()
        amount = 0.0
        mode = False
        for aml in batch_result['lines']:
            if early_payment_discount and aml._is_eligible_for_early_payment_discount(aml.currency_id, self.payment_date):
                amount += aml.discount_amount_currency
                mode = 'early_payment'
            else:
                amount += aml.amount_residual_currency
        return abs(amount), mode

    def _get_total_amount_in_wizard_currency_to_full_reconcile(self, batch_result, early_payment_discount=True):
        """ Compute the total amount needed in the currency of the wizard to fully reconcile the batch of journal
        items passed as parameter.

        :param batch_result:    A batch returned by '_get_batches'.
        :return:                An amount in the currency of the wizard.
        """
        self.ensure_one()
        comp_curr = self.company_id.currency_id
        if self.source_currency_id == self.currency_id:
            # Same currency (manage the early payment discount).
            return self._get_total_amount_using_same_currency(batch_result, early_payment_discount=early_payment_discount)
        elif self.source_currency_id != comp_curr and self.currency_id == comp_curr:
            # Foreign currency on source line but the company currency one on the opposite line.
            return self.source_currency_id._convert(
                self.source_amount_currency,
                comp_curr,
                self.company_id,
                self.payment_date,
            ), False
        elif self.source_currency_id == comp_curr and self.currency_id != comp_curr:
            # Company currency on source line but a foreign currency one on the opposite line.
            residual_amount = 0.0
            for aml in batch_result['lines']:
                if not aml.move_id.payment_id and not aml.move_id.statement_line_id:
                    conversion_date = self.payment_date
                else:
                    conversion_date = aml.date
                residual_amount += comp_curr._convert(
                    aml.amount_residual,
                    self.currency_id,
                    self.company_id,
                    conversion_date,
                )
            return abs(residual_amount), False
        else:
            # Foreign currency on payment different than the one set on the journal entries.
            return comp_curr._convert(
                self.source_amount,
                self.currency_id,
                self.company_id,
                self.payment_date,
            ), False

    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date')
    def _compute_amount(self):
        for wizard in self:
            if wizard.source_currency_id and wizard.can_edit_wizard:
                batch_result = wizard._get_batches()[0]
                wizard.amount = wizard._get_total_amount_in_wizard_currency_to_full_reconcile(batch_result)[0]
            else:
                # The wizard is not editable so no partial payment allowed and then, 'amount' is not used.
                wizard.amount = None

    @api.depends('can_edit_wizard', 'payment_date', 'currency_id', 'amount')
    def _compute_early_payment_discount_mode(self):
        for wizard in self:
            if wizard.can_edit_wizard and wizard.currency_id:
                batch_result = wizard._get_batches()[0]
                total_amount_residual_in_wizard_currency, mode = wizard._get_total_amount_in_wizard_currency_to_full_reconcile(batch_result)
                wizard.early_payment_discount_mode = \
                    wizard.currency_id.compare_amounts(wizard.amount, total_amount_residual_in_wizard_currency) == 0 \
                    and mode == 'early_payment'
            else:
                wizard.early_payment_discount_mode = False

    @api.depends('can_edit_wizard', 'amount')
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch_result = wizard._get_batches()[0]
                total_amount_residual_in_wizard_currency = wizard\
                    ._get_total_amount_in_wizard_currency_to_full_reconcile(batch_result, early_payment_discount=False)[0]
                wizard.payment_difference = total_amount_residual_in_wizard_currency - wizard.amount
            else:
                wizard.payment_difference = 0.0

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

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)

        if 'line_ids' in fields_list and 'line_ids' not in res:

            # Retrieve moves to pay from the context.

            if self._context.get('active_model') == 'account.move':
                lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids
            elif self._context.get('active_model') == 'account.move.line':
                lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
            else:
                raise UserError(_(
                    "The register payment wizard should only be called on account.move or account.move.line records."
                ))

            if 'journal_id' in res and not self.env['account.journal'].browse(res['journal_id'])\
                    .filtered_domain([('company_id', '=', lines.company_id.id), ('type', 'in', ('bank', 'cash'))]):
                # default can be inherited from the list view, should be computed instead
                del res['journal_id']

            # Keep lines having a residual amount to pay.
            available_lines = self.env['account.move.line']
            for line in lines:
                if line.move_id.state != 'posted':
                    raise UserError(_("You can only register payment for posted journal entries."))

                if line.account_type not in ('asset_receivable', 'liability_payable'):
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
                raise UserError(_("You can't register a payment because there is nothing left to pay on the selected journal items."))
            if len(lines.company_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different companies."))
            if len(set(available_lines.mapped('account_type'))) > 1:
                raise UserError(_("You can't register payments for journal items being either all inbound, either all outbound."))

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
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'write_off_line_vals': [],
        }

        conversion_rate = self.env['res.currency']._get_conversion_rate(
            self.currency_id,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date,
        )

        if self.payment_difference_handling == 'reconcile':

            if self.early_payment_discount_mode:
                epd_aml_values_list = []
                for aml in batch_result['lines']:
                    if aml._is_eligible_for_early_payment_discount(self.currency_id, self.payment_date):
                        epd_aml_values_list.append({
                            'aml': aml,
                            'amount_currency': -aml.amount_residual_currency,
                            'balance': aml.company_currency_id.round(-aml.amount_residual_currency * conversion_rate),
                        })

                open_amount_currency = self.payment_difference * (-1 if self.payment_type == 'outbound' else 1)
                open_balance = self.company_id.currency_id.round(open_amount_currency * conversion_rate)
                early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
                for aml_values_list in early_payment_values.values():
                    payment_vals['write_off_line_vals'] += aml_values_list

            elif not self.currency_id.is_zero(self.payment_difference):
                if self.payment_type == 'inbound':
                    # Receive money.
                    write_off_amount_currency = self.payment_difference
                else: # if self.payment_type == 'outbound':
                    # Send money.
                    write_off_amount_currency = -self.payment_difference

                write_off_balance = self.company_id.currency_id.round(write_off_amount_currency * conversion_rate)
                payment_vals['write_off_line_vals'].append({
                    'name': self.writeoff_label,
                    'account_id': self.writeoff_account_id.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': write_off_amount_currency,
                    'balance': write_off_balance,
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
            'ref': self._get_batch_communication(batch_result),
            'journal_id': self.journal_id.id,
            'currency_id': batch_values['source_currency_id'],
            'partner_id': batch_values['partner_id'],
            'partner_bank_id': partner_bank_id,
            'payment_method_line_id': payment_method_line.id,
            'destination_account_id': batch_result['lines'][0].account_id.id,
            'write_off_line_vals': [],
        }

        total_amount, mode = self._get_total_amount_using_same_currency(batch_result)
        currency = self.env['res.currency'].browse(batch_values['source_currency_id'])
        if mode == 'early_payment':
            payment_vals['amount'] = total_amount

            conversion_rate = self.env['res.currency']._get_conversion_rate(
                currency,
                self.company_id.currency_id,
                self.company_id,
                self.payment_date,
            )

            epd_aml_values_list = []
            for aml in batch_result['lines']:
                if aml._is_eligible_for_early_payment_discount(currency, self.payment_date):
                    epd_aml_values_list.append({
                        'aml': aml,
                        'amount_currency': -aml.amount_residual_currency,
                        'balance': aml.company_currency_id.round(-aml.amount_residual_currency * conversion_rate),
                    })

            open_amount_currency = (batch_values['source_amount_currency'] - total_amount) * (-1 if batch_values['payment_type'] == 'outbound' else 1)
            open_balance = self.company_id.currency_id.round(open_amount_currency * conversion_rate)
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
                                            to which a payment will be created (see '_get_batches').
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
            if edit_mode:
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
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        payments = self.env['account.payment']
        for vals in to_process:
            payments |= vals['payment']
        payments.action_post()

    def _reconcile_payments(self, to_process, edit_mode=False):
        """ Reconcile the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('reconciled', '=', False),
        ]
        for vals in to_process:
            payment_lines = vals['payment'].line_ids.filtered_domain(domain)
            lines = vals['to_reconcile']

            for account in payment_lines.account_id:
                (payment_lines + lines)\
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                    .reconcile()

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': first_batch_result['lines'],
                'batch': first_batch_result,
            })
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
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

        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments

    def action_create_payments(self):
        payments = self._create_payments()

        if self._context.get('dont_redirect_to_payments'):
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
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action
