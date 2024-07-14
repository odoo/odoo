# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountBatchPayment(models.Model):
    _name = "account.batch.payment"
    _description = "Batch Payment"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, copy=False, string='Reference')
    date = fields.Date(required=True, copy=False, default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('sent', 'Sent'),
        ('reconciled', 'Reconciled'),
    ], store=True, compute='_compute_state', default='draft', tracking=True)
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank',
        check_company=True,
        domain=[('type', '=', 'bank')],
        tracking=True,
    )
    payment_ids = fields.One2many('account.payment', 'batch_payment_id', string="Payments", required=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, readonly=True)
    company_currency_id = fields.Many2one(
        string="Company Currency",
        related='journal_id.company_id.currency_id',
        store=True,
    )
    amount_residual = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_payment_ids',
        store=True,
    )
    amount_residual_currency = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_from_payment_ids',
        store=True,
    )
    amount = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_from_payment_ids',
        store=True,
    )
    batch_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True, default='inbound', tracking=True)
    payment_method_id = fields.Many2one(
        comodel_name='account.payment.method',
        string='Payment Method', store=True, readonly=False,
        compute='_compute_payment_method_id',
        domain="[('id', 'in', available_payment_method_ids)]",
        help="The payment method used by the payments in this batch.", tracking=True)
    available_payment_method_ids = fields.Many2many(
        comodel_name='account.payment.method',
        compute='_compute_available_payment_method_ids')
    payment_method_code = fields.Char(related='payment_method_id.code', tracking=True)
    export_file_create_date = fields.Date(string='Generation Date', default=fields.Date.today, readonly=True, help="Creation date of the related export file.", copy=False)
    export_file = fields.Binary(string='File', readonly=True, help="Export file related to this batch", copy=False)
    export_filename = fields.Char(string='File Name', help="Name of the export file generated for this batch", store=True, copy=False)

    file_generation_enabled = fields.Boolean(help="Whether or not this batch payment should display the 'Generate File' button instead of 'Print' in form view.", compute='_compute_file_generation_enabled')

    @api.depends('batch_type', 'journal_id', 'payment_ids')
    def _compute_payment_method_id(self):
        ''' Compute the 'payment_method_id' field.
        This field is not computed in '_compute_available_payment_method_ids' because it's a stored editable one.
        '''
        for batch in self:
            if batch.payment_ids:
                batch.payment_method_id = batch.payment_ids.payment_method_line_id[0].payment_method_id
                continue

            if not batch.journal_id:
                batch.available_payment_method_ids = False
                batch.payment_method_id = False
                continue

            available_payment_method_lines = batch.journal_id._get_available_payment_method_lines(batch.batch_type)

            batch.available_payment_method_ids = available_payment_method_lines.mapped('payment_method_id')

            # Select the first available one by default.
            if batch.available_payment_method_ids:
                batch.payment_method_id = batch.available_payment_method_ids[0]._origin
            else:
                batch.payment_method_id = False

    @api.depends('batch_type', 'journal_id')
    def _compute_available_payment_method_ids(self):
        for batch in self:
            available_payment_method_lines = batch.journal_id._get_available_payment_method_lines(batch.batch_type)
            batch.available_payment_method_ids = available_payment_method_lines.mapped('payment_method_id')

    @api.depends('payment_ids.move_id.is_move_sent', 'payment_ids.is_matched')
    def _compute_state(self):
        for batch in self:
            if batch.payment_ids and all(pay.is_matched and pay.is_move_sent for pay in batch.payment_ids):
                batch.state = 'reconciled'
            elif batch.payment_ids and all(pay.is_move_sent for pay in batch.payment_ids):
                batch.state = 'sent'
            else:
                batch.state = 'draft'

    @api.depends('payment_method_id')
    def _compute_file_generation_enabled(self):
        for record in self:
            record.file_generation_enabled = record.payment_method_id.code in record._get_methods_generating_files()

    def _get_methods_generating_files(self):
        """ Hook for extension. Any payment method whose code stands in the list
        returned by this function will see the "print" button disappear on batch
        payments form when it gets selected and an 'Export file' appear instead.
        """
        return []

    @api.depends('journal_id')
    def _compute_currency(self):
        for batch in self:
            batch.currency_id = batch.journal_id.currency_id or batch.company_currency_id or self.env.company.currency_id

    @api.depends('currency_id', 'payment_ids.amount')
    def _compute_from_payment_ids(self):
        for batch in self:
            amount = 0.0
            amount_residual = 0.0
            amount_residual_currency = 0.0
            for payment in batch.payment_ids:
                liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
                for line in liquidity_lines:
                    amount += line.currency_id._convert(
                        from_amount=line.amount_currency,
                        to_currency=batch.currency_id,
                        company=line.company_id,
                        date=line.date,
                    )
                    amount_residual += line.amount_residual
                    amount_residual_currency += line.amount_residual_currency

            batch.amount_residual = amount_residual
            batch.amount = amount
            batch.amount_residual_currency = amount_residual_currency

    @api.constrains('batch_type', 'journal_id', 'payment_ids')
    def _check_payments_constrains(self):
        for record in self:
            all_companies = set(record.payment_ids.mapped('company_id'))
            if len(all_companies) > 1:
                raise ValidationError(_("All payments in the batch must belong to the same company."))
            all_journals = set(record.payment_ids.mapped('journal_id'))
            if len(all_journals) > 1 or (record.payment_ids and record.payment_ids[:1].journal_id != record.journal_id):
                raise ValidationError(_("The journal of the batch payment and of the payments it contains must be the same."))
            all_types = set(record.payment_ids.mapped('payment_type'))
            if all_types and record.batch_type not in all_types:
                raise ValidationError(_("The batch must have the same type as the payments it contains."))
            all_payment_methods = record.payment_ids.payment_method_id
            if len(all_payment_methods) > 1:
                raise ValidationError(_("All payments in the batch must share the same payment method."))
            if all_payment_methods and record.payment_method_id not in all_payment_methods:
                raise ValidationError(_("The batch must have the same payment method as the payments it contains."))
            payment_null = record.payment_ids.filtered(lambda p: p.amount == 0)
            if payment_null:
                raise ValidationError(_('You cannot add payments with zero amount in a Batch Payment.'))
            non_posted = record.payment_ids.filtered(lambda p: p.state != 'posted')
            if non_posted:
                raise ValidationError(_('You cannot add payments that are not posted.'))

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            vals['name'] = self._get_batch_name(
                vals.get('batch_type'),
                vals.get('date', today),
                vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'batch_type' in vals:
            vals['name'] = self.with_context(default_journal_id=self.journal_id.id)._get_batch_name(vals['batch_type'], self.date, vals)

        rslt = super(AccountBatchPayment, self).write(vals)

        return rslt

    @api.model
    def _get_batch_name(self, batch_type, sequence_date, vals):
        if not vals.get('name'):
            sequence_code = 'account.inbound.batch.payment'
            if batch_type == 'outbound':
                sequence_code = 'account.outbound.batch.payment'
            return self.env['ir.sequence'].with_context(sequence_date=sequence_date).next_by_code(sequence_code)
        return vals['name']

    @api.depends('state')
    def _compute_display_name(self):
        state_values = dict(self._fields['state'].selection)
        for batch in self:
            batch.display_name = f'{batch.name} ({state_values.get(batch.state)})'

    def validate_batch(self):
        """ Verifies the content of a batch and proceeds to its sending if possible.
        If not, opens a wizard listing the errors and/or warnings encountered.
        """
        self.ensure_one()
        if not self.payment_ids:
            raise UserError(_("Cannot validate an empty batch. Please add some payments to it first."))

        errors = not self.export_file and self.check_payments_for_errors() or []  # We don't re-check for errors if we are regenerating the file (we know there aren't any)
        warnings = self.check_payments_for_warnings()
        if errors or warnings:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.batch.error.wizard',
                'target': 'new',
                'res_id': self.env['account.batch.error.wizard'].create_from_errors_list(self, errors, warnings).id,
            }

        return self._send_after_validation()

    def validate_batch_button(self):
        return self.validate_batch()

    def _send_after_validation(self):
        """ Sends the payments of a batch (possibly generating an export file)
        once the batch has been validated.
        """

        self.ensure_one()
        if self.payment_ids:
            self.payment_ids.mark_as_sent()

            if self.file_generation_enabled:
                return self.export_batch_payment()

    def check_payments_for_warnings(self):
        """ Checks the payments of this batch and returns (if relevant) some
        warnings about them. These warnings are not to be confused with errors,
        they are only messgaes displayed to make sure the user is aware of some
        specificities in the payments he's put in the batch. He will be able to
        ignore them.

        :return:    A list of dictionaries, each one corresponding to a distinct
                    warning and containing the following keys:
                    - 'title': A short name for the warning (mandatory)
                    - 'records': The recordset of payments concerned by this warning (mandatory)
                    - 'help': A help text to give the user further information
                              on the reason this warning exists (optional)
        """
        return []

    def check_payments_for_errors(self):
        """ Goes through all the payments of the batches contained in this
        record set, and returns the ones that would impeach batch validation,
        in such a way that the payments impeaching validation for the same reason
        are grouped under a common error message. This function is a hook for
        extension for modules making a specific use of batch payments, such as SEPA
        ones.

        :return:    A list of dictionaries, each one corresponding to a distinct
                    error and containing the following keys:
                    - 'title': A short name for the error (mandatory)
                    - 'records': The recordset of payments facing this error (mandatory)
                    - 'help': A help text to give the user further information
                              on how to solve the error (optional)
        """
        self.ensure_one()
        #We first try to post all the draft batch payments
        rslt = self._check_and_post_draft_payments(self.payment_ids.filtered(lambda x: x.state == 'draft'))

        wrong_state_payments = self.payment_ids.filtered(lambda x: x.state != 'posted')

        if wrong_state_payments:
            rslt.append({
                'title': _("Payments must be posted to be added to a batch."),
                'records': wrong_state_payments,
                'help': _("Set payments state to \"posted\".")
            })

        if self.batch_type == 'outbound':
            not_allowed_payments = self.payment_ids.filtered(lambda x: x.partner_bank_id and not x.partner_bank_id.allow_out_payment)
            if not_allowed_payments:
                rslt.append({
                    'code': 'out_payment_not_allowed',
                    'title': _("Some recipient accounts do not allow out payments."),
                    'records': not_allowed_payments,
                    'help': _("Target another recipient account or allow sending money to the current one.")
                })

        sent_payments = self.payment_ids.filtered(lambda x: x.is_move_sent)
        if sent_payments:
            rslt.append({
                'title': _("Some payments have already been sent."),
                'records': sent_payments,
            })

        if self.batch_type == 'inbound':
            pmls = self.journal_id.inbound_payment_method_line_ids
            default_payment_account = self.journal_id.company_id.account_journal_payment_debit_account_id
        else:
            pmls = self.journal_id.outbound_payment_method_line_ids
            default_payment_account = self.journal_id.company_id.account_journal_payment_credit_account_id
        pmls = pmls.filtered(lambda x: x.payment_method_id == self.payment_method_id)
        no_statement_reconciliation = self.journal_id.default_account_id == (pmls.payment_account_id[:1] or default_payment_account)
        bank_reconciled_payments = self.payment_ids.filtered(lambda x: x.is_matched)
        if bank_reconciled_payments and not no_statement_reconciliation:
            rslt.append({
                'title': _("Some payments have already been matched with a bank statement."),
                'records': bank_reconciled_payments,
            })

        return rslt

    def _check_and_post_draft_payments(self, draft_payments):
        """ Tries posting each of the draft payments contained in this batch.
        If it fails and raise a UserError, it is catched and the process continues
        on the following payments. All the encountered errors are then returned
        withing a dictionary, in the same fashion as check_payments_for_errors.
        """
        exceptions_mapping = {}
        for payment in draft_payments:
            try:
                payment.action_post()
            except UserError as e:
                name = e.args[0]
                if name in exceptions_mapping:
                    exceptions_mapping[name] += payment
                else:
                    exceptions_mapping[name] = payment

        return [{'title': error, 'records': pmts} for error, pmts in exceptions_mapping.items()]

    def export_batch_payment(self):
        #export and save the file for each batch payment
        self.check_access_rights('write')
        self.check_access_rule('write')
        for record in self.sudo():
            record = record.with_company(record.journal_id.company_id)
            export_file_data = record._generate_export_file()
            record.export_file = export_file_data['file']
            record.export_filename = export_file_data['filename']
            record.export_file_create_date = fields.Date.today()
            record.message_post(
                attachments=[
                    (record.export_filename, base64.decodebytes(record.export_file)),
                ]
            )

    def print_batch_payment(self):
        return self.env.ref('account_batch_payment.action_print_batch_payment').report_action(self, config=False)

    def _generate_export_file(self):
        """ To be overridden by modules adding support for different export format.
            This function returns False if no export file could be generated
            for this batch. Otherwise, it returns a dictionary containing the following keys:
            - file: the content of the generated export file, in base 64.
            - filename: the name of the generated file
            - warning: (optional) the warning message to display

        """
        self.ensure_one()
        return False
