# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, ValidationError, UserError


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
    company_id = fields.Many2one('res.company', related='journal_id.company_id', readonly=True)
    payment_ids = fields.One2many('account.payment', 'batch_payment_id', string="Payments", required=True)
    payment_ids_domain = fields.Char(compute='_compute_payment_ids_domain')
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
    invalid_sct_partners_ids = fields.Many2many('res.partner', compute='_compute_invalid_sct_partners_ids')

    @api.depends('batch_type', 'journal_id', 'payment_method_id')
    def _compute_payment_ids_domain(self):
        for batch in self:
            batch.payment_ids_domain = str([
                ('batch_payment_id', '=', False),
                ('state', 'in', self._valid_payment_states()),
                ('is_sent', '=', False),
                ('payment_method_id', '=', batch.payment_method_id.id),
                ('journal_id', '=', batch.journal_id.id),
                ('payment_type', '=', batch.batch_type),
                ('amount', '!=', 0),
            ])

    def _valid_payment_states(self):
        return ['in_process', 'paid'] if self.env['account.move']._get_invoice_in_payment_state() == 'paid' else ['in_process']

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

    @api.depends('payment_ids.is_sent', 'payment_ids.is_matched')
    def _compute_state(self):
        for batch in self:
            if batch.payment_ids and all(pay.is_matched and pay.is_sent for pay in batch.payment_ids.filtered(lambda p: p.state not in ('canceled', 'rejected'))):
                batch.state = 'reconciled'
            elif batch.payment_ids and all(pay.is_sent for pay in batch.payment_ids.filtered(lambda p: p.state not in ('canceled', 'rejected'))):
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

    @api.depends('currency_id', 'payment_ids.amount', 'payment_ids.is_matched', 'payment_ids.state')
    def _compute_from_payment_ids(self):
        valid_payment_states = self._valid_payment_states()
        for batch in self:
            amount = 0.0
            amount_residual = 0.0
            amount_residual_currency = 0.0
            for payment in batch.payment_ids:
                if payment.move_id:
                    liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
                    for line in liquidity_lines:
                        if line.currency_id == batch.currency_id:
                            amount += line.amount_currency
                        elif batch.currency_id == line.company_currency_id:
                            amount += line.balance
                        else:
                            amount += line.company_currency_id._convert(
                                from_amount=line.balance,
                                to_currency=batch.currency_id,
                                company=line.company_id,
                                date=line.date,
                            )

                        if payment.state in valid_payment_states:
                            amount_residual += line.amount_residual
                            if line.currency_id == batch.currency_id:
                                amount_residual_currency += line.amount_residual_currency
                            elif batch.currency_id == line.company_currency_id:
                                amount_residual_currency += line.amount_residual
                            else:
                                amount_residual_currency += line.company_currency_id._convert(
                                    from_amount=line.amount_residual,
                                    to_currency=batch.currency_id,
                                    company=line.company_id,
                                    date=line.date,
                                )
                else:
                    if payment.currency_id == batch.currency_id:
                        payment_amount = payment.amount_signed
                    elif batch.currency_id == payment.company_currency_id:
                        payment_amount = payment.amount_company_currency_signed
                    else:
                        payment_amount = payment.company_currency_id._convert(
                            from_amount=payment.amount_company_currency_signed,
                            to_currency=batch.currency_id,
                            company=payment.company_id,
                            date=payment.date,
                        )
                    amount += payment_amount
                    if payment.state in valid_payment_states:
                        amount_residual_currency += payment_amount
                        if payment.currency_id == batch.company_id.currency_id:
                            amount_residual += payment.amount_signed
                        elif batch.currency_id == payment.company_currency_id:
                            amount_residual += payment.amount_company_currency_signed
                        else:
                            amount_residual += payment.company_currency_id._convert(
                                from_amount=payment.amount_company_currency_signed,
                                to_currency=batch.company_id.currency_id,
                                company=payment.company_id,
                                date=payment.date,
                            )

            batch.amount_residual = amount_residual
            batch.amount = amount
            batch.amount_residual_currency = amount_residual_currency

    @api.constrains('batch_type', 'journal_id', 'payment_ids', 'payment_method_id')
    def _check_payments_constrains(self):
        for record in self:
            if record.payment_ids and record.journal_id != record.payment_ids.journal_id:
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

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        all_payment_ids = []
        for vals in vals_list:
            vals['name'] = self._get_batch_name(
                vals.get('batch_type'),
                vals.get('date', today),
                vals)
            if 'payment_ids' in vals:
                payments = self.new({'payment_ids': vals['payment_ids']}).payment_ids
                if payments._origin.batch_payment_id:
                    raise ValidationError(_('You cannot create a batch with payments that are already in another batch.'))
                # Collect all payment IDs
                all_payment_ids.extend(payments.ids)

        if len(all_payment_ids) != len(set(all_payment_ids)):
            raise ValidationError(_('You cannot create batches with overlapping payments.'))
        return super().create(vals_list)

    def write(self, vals):
        if 'batch_type' in vals:
            vals['name'] = self.with_context(default_journal_id=self.journal_id.id)._get_batch_name(vals['batch_type'], self.date, vals)
        if 'payment_ids' in vals:
            if len(self) > 1:
                raise ValidationError(_('You cannot add the same payment to multiple batches.'))
            original_payments = self.new({'payment_ids': vals['payment_ids']}).payment_ids._origin
            if original_payments.batch_payment_id - self:
                raise ValidationError(_('You cannot create a batch with payments that are already in another batch.'))

        rslt = super(AccountBatchPayment, self).write(vals)

        return rslt

    def unlink(self):
        for batch in self:
            for payment in batch.payment_ids:
                payment.message_post(
                    body=_('Payment removed from batch %s', batch._get_html_link(title=batch.name)),
                    message_type='comment',
                )
        return super().unlink()

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

    @api.depends('payment_method_id', 'payment_ids.partner_id.country_id', 'payment_ids.partner_id.city')
    def _compute_invalid_sct_partners_ids(self):
        sepa_batches = self.filtered(lambda b: b.payment_method_id.code == 'sepa_ct')
        for batch in sepa_batches:
            invalid_partners = self.env['res.partner']
            for partner in batch.payment_ids.partner_id:
                # sudo needed for accountant users that are not in hr (employee_ids)
                addresses = partner.sudo()._get_all_addr()
                has_valid_address = any(
                    addr.get('city') and addr.get('country')
                    for addr in addresses
                )
                if not has_valid_address:
                    invalid_partners |= partner

            batch.invalid_sct_partners_ids = invalid_partners
        (self - sepa_batches).invalid_sct_partners_ids = self.env['res.partner']

    def action_invalid_partners_from_sct(self):
        return self.invalid_sct_partners_ids._get_records_action(name=_("Invalid Partners"))

    def validate_batch(self):
        """ Verifies the content of a batch and proceeds to its sending if possible.
        If not, opens a wizard listing the errors and/or warnings encountered.
        """
        validate_action = self._check_batch_validity()
        if validate_action:
            return validate_action
        return self._send_after_validation()

    def _check_batch_validity(self):
        self.ensure_one()
        if not self.payment_ids:
            raise UserError(_("Cannot validate an empty batch. Please add some payments to it first."))

        errors = not self.export_file and self.check_payments_for_errors() or []  # We don't re-check for errors if we are regenerating the file (we know there aren't any)
        warnings = self.check_payments_for_warnings()
        if errors or warnings:
            if len(errors) == 1 and not warnings:
                raise RedirectWarning(
                    message=errors[0]['title'] + '\n' + errors[0].get('help', ''),
                    action=errors[0].get('records', self.env['account.payment'])._get_records_action(name=_('Payments in Error')),
                    button_text=_('Check Payments')
                )
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.batch.error.wizard',
                'target': 'new',
                'res_id': self.env['account.batch.error.wizard'].create_from_errors_list(self, errors, warnings).id,
            }

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

        valid_payment_states = self._valid_payment_states()
        wrong_state_payments = self.payment_ids.filtered(lambda x: x.state not in valid_payment_states)

        if wrong_state_payments:
            rslt.append({
                'title': _("To validate the batch, payments must be in process. But some are already matched with a bank statement."),
                'records': wrong_state_payments,
                'help': _("Remove the payments from the batch or change their state.")
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

        sent_payments = self.payment_ids.filtered(lambda x: x.is_sent)
        if sent_payments:
            rslt.append({
                'title': _("Some payments have already been sent."),
                'records': sent_payments,
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
        self.check_access('write')
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
