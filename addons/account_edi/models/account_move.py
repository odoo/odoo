# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_document_ids = fields.One2many(
        comodel_name='account.edi.document',
        inverse_name='move_id')
    edi_state = fields.Selection(
        selection=[('to_send', 'To Send'), ('sent', 'Sent'), ('to_cancel', 'To Cancel'), ('cancelled', 'Cancelled')],
        string="Electronic invoicing",
        store=True,
        compute='_compute_edi_state',
        help='The aggregated state of all the EDIs of this move')
    edi_error_count = fields.Integer(
        compute='_compute_edi_error_count',
        help='How many EDIs are in error for this move ?')
    edi_web_services_to_process = fields.Text(
        compute='_compute_edi_web_services_to_process',
        help="Technical field to display the documents that will be processed by the CRON")
    edi_show_cancel_button = fields.Boolean(
        compute='_compute_edi_show_cancel_button')

    @api.depends('edi_document_ids.state')
    def _compute_edi_state(self):
        for move in self:
            all_states = set(move.edi_document_ids.filtered(lambda d: d.edi_format_id._needs_web_services()).mapped('state'))
            if all_states == {'sent'}:
                move.edi_state = 'sent'
            elif all_states == {'cancelled'}:
                move.edi_state = 'cancelled'
            elif 'to_send' in all_states:
                move.edi_state = 'to_send'
            elif 'to_cancel' in all_states:
                move.edi_state = 'to_cancel'
            else:
                move.edi_state = False

    @api.depends('edi_document_ids.error')
    def _compute_edi_error_count(self):
        for move in self:
            move.edi_error_count = len(move.edi_document_ids.filtered(lambda d: d.error))

    @api.depends(
        'edi_document_ids',
        'edi_document_ids.state',
        'edi_document_ids.edi_format_id',
        'edi_document_ids.edi_format_id.name')
    def _compute_edi_web_services_to_process(self):
        for move in self:
            to_process = move.edi_document_ids.filtered(lambda d: d.state in ['to_send', 'to_cancel'])
            format_web_services = to_process.edi_format_id.filtered(lambda f: f._needs_web_services())
            move.edi_web_services_to_process = ', '.join(f.name for f in format_web_services)

    @api.depends('restrict_mode_hash_table', 'state')
    def _compute_show_reset_to_draft_button(self):
        # OVERRIDE
        super()._compute_show_reset_to_draft_button()

        for move in self:
            for doc in move.edi_document_ids:
                if doc.edi_format_id._needs_web_services() \
                        and doc.attachment_id \
                        and doc.state in ('sent', 'to_cancel') \
                        and move.is_invoice(include_receipts=True) \
                        and doc.edi_format_id._is_required_for_invoice(move):
                    move.show_reset_to_draft_button = False
                    break

    @api.depends(
        'state',
        'edi_document_ids.state',
        'edi_document_ids.attachment_id')
    def _compute_edi_show_cancel_button(self):
        for move in self:
            if move.state != 'posted':
                move.edi_show_cancel_button = False
                continue

            move.edi_show_cancel_button = any([doc.edi_format_id._needs_web_services()
                                               and doc.attachment_id
                                               and doc.state == 'sent'
                                               and move.is_invoice(include_receipts=True)
                                               and doc.edi_format_id._is_required_for_invoice(move)
                                              for doc in move.edi_document_ids])

    ####################################################
    # Export Electronic Document
    ####################################################

    @api.model
    def _add_edi_tax_values(self, results, grouping_key, serialized_grouping_key, tax_values):
        # Add to global results.
        results['tax_amount'] += tax_values['tax_amount']
        results['tax_amount_currency'] += tax_values['tax_amount_currency']

        # Add to tax details.
        tax_details = results['tax_details'][serialized_grouping_key]
        tax_details.update(grouping_key)
        if tax_values['base_line_id'] not in set(x['base_line_id'] for x in tax_details['group_tax_details']):
            tax_details['base_amount'] += tax_values['base_amount']
            tax_details['base_amount_currency'] += tax_values['base_amount_currency']

        tax_details['tax_amount'] += tax_values['tax_amount']
        tax_details['tax_amount_currency'] += tax_values['tax_amount_currency']
        tax_details['exemption_reason'] = tax_values['tax_id'].name
        tax_details['group_tax_details'].append(tax_values)

    def _prepare_edi_tax_details(self, filter_to_apply=None, filter_invl_to_apply=None, grouping_key_generator=None):
        ''' Compute amounts related to taxes for the current invoice.
        :param filter_to_apply:         Optional filter to exclude some tax values from the final results.
                                        The filter is defined as a method getting a dictionary as parameter
                                        representing the tax values for a single repartition line.
                                        This dictionary contains:
            'base_line_id':             An account.move.line record.
            'tax_id':                   An account.tax record.
            'tax_repartition_line_id':  An account.tax.repartition.line record.
            'base_amount':              The tax base amount expressed in company currency.
            'tax_amount':               The tax amount expressed in company currency.
            'base_amount_currency':     The tax base amount expressed in foreign currency.
            'tax_amount_currency':      The tax amount expressed in foreign currency.
                                        If the filter is returning False, it means the current tax values will be
                                        ignored when computing the final results.
        :param grouping_key_generator:  Optional method used to group tax values together. By default, the tax values
                                        are grouped by tax. This parameter is a method getting a dictionary as parameter
                                        (same signature as 'filter_to_apply').
                                        This method must returns a dictionary where values will be used to create the
                                        grouping_key to aggregate tax values together. The returned dictionary is added
                                        to each tax details in order to retrieve the full grouping_key later.
        :return:                        The full tax details for the current invoice and for each invoice line
                                        separately. The returned dictionary is the following:
            'base_amount':              The total tax base amount in company currency for the whole invoice.
            'tax_amount':               The total tax amount in company currency for the whole invoice.
            'base_amount_currency':     The total tax base amount in foreign currency for the whole invoice.
            'tax_amount_currency':      The total tax amount in foreign currency for the whole invoice.
            'tax_details':              A mapping of each grouping key (see 'grouping_key_generator') to a dictionary
                                        containing:
                'base_amount':              The tax base amount in company currency for the current group.
                'tax_amount':               The tax amount in company currency for the current group.
                'base_amount_currency':     The tax base amount in foreign currency for the current group.
                'tax_amount_currency':      The tax amount in foreign currency for the current group.
                'group_tax_details':        The list of all tax values aggregated into this group.
            'invoice_line_tax_details': A mapping of each invoice line to a dictionary containing:
                'base_amount':          The total tax base amount in company currency for the whole invoice line.
                'tax_amount':           The total tax amount in company currency for the whole invoice line.
                'base_amount_currency': The total tax base amount in foreign currency for the whole invoice line.
                'tax_amount_currency':  The total tax amount in foreign currency for the whole invoice line.
                'tax_details':          A mapping of each grouping key (see 'grouping_key_generator') to a dictionary
                                        containing:
                    'base_amount':          The tax base amount in company currency for the current group.
                    'tax_amount':           The tax amount in company currency for the current group.
                    'base_amount_currency': The tax base amount in foreign currency for the current group.
                    'tax_amount_currency':  The tax amount in foreign currency for the current group.
                    'group_tax_details':    The list of all tax values aggregated into this group.
        '''
        self.ensure_one()

        def _serialize_python_dictionary(vals):
            return '-'.join(str(vals[k]) for k in sorted(vals.keys()))

        def default_grouping_key_generator(tax_values):
            return {'tax': tax_values['tax_id']}

        # Compute the taxes values for each invoice line.

        invoice_lines = self.invoice_line_ids.filtered(lambda line: not line.display_type)
        if filter_invl_to_apply:
            invoice_lines = invoice_lines.filtered(filter_invl_to_apply)

        invoice_lines_tax_values_dict = {}
        sign = -1 if self.is_inbound() else 1
        for invoice_line in invoice_lines:
            taxes_res = invoice_line.tax_ids.compute_all(
                invoice_line.price_unit * (1 - (invoice_line.discount / 100.0)),
                currency=invoice_line.currency_id,
                quantity=invoice_line.quantity,
                product=invoice_line.product_id,
                partner=invoice_line.partner_id,
                is_refund=invoice_line.move_id.move_type in ('in_refund', 'out_refund'),
            )
            tax_values_list = invoice_lines_tax_values_dict[invoice_line] = []
            rate = abs(invoice_line.balance) / abs(invoice_line.amount_currency) if invoice_line.amount_currency else 0.0
            for tax_res in taxes_res['taxes']:
                tax_values_list.append({
                    'base_line_id': invoice_line,
                    'tax_id': self.env['account.tax'].browse(tax_res['id']),
                    'tax_repartition_line_id': self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id']),
                    'base_amount': sign * invoice_line.company_currency_id.round(tax_res['base'] * rate),
                    'tax_amount': sign * invoice_line.company_currency_id.round(tax_res['amount'] * rate),
                    'base_amount_currency': sign * tax_res['base'],
                    'tax_amount_currency': sign * tax_res['amount'],
                })
        grouping_key_generator = grouping_key_generator or default_grouping_key_generator

        # Apply 'filter_to_apply'.

        if filter_to_apply:
            invoice_lines_tax_values_dict = {
                invoice_line: [x for x in tax_values_list if filter_to_apply(x)]
                for invoice_line, tax_values_list in invoice_lines_tax_values_dict.items()
            }

        # Initialize the results dict.

        invoice_global_tax_details = {
            'base_amount': 0.0,
            'tax_amount': 0.0,
            'base_amount_currency': 0.0,
            'tax_amount_currency': 0.0,
            'tax_details': defaultdict(lambda: {
                'base_amount': 0.0,
                'tax_amount': 0.0,
                'base_amount_currency': 0.0,
                'tax_amount_currency': 0.0,
                'group_tax_details': [],
            }),
            'invoice_line_tax_details': defaultdict(lambda: {
                'base_amount': 0.0,
                'tax_amount': 0.0,
                'base_amount_currency': 0.0,
                'tax_amount_currency': 0.0,
                'tax_details': defaultdict(lambda: {
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                    'base_amount_currency': 0.0,
                    'tax_amount_currency': 0.0,
                    'group_tax_details': [],
                }),
            }),
        }

        # Apply 'grouping_key_generator' to 'invoice_lines_tax_values_list' and add all values to the final results.

        for invoice_line in invoice_lines:
            tax_values_list = invoice_lines_tax_values_dict[invoice_line]

            # Add to invoice global tax amounts.
            invoice_global_tax_details['base_amount'] += invoice_line.balance
            invoice_global_tax_details['base_amount_currency'] += invoice_line.amount_currency

            for tax_values in tax_values_list:
                grouping_key = grouping_key_generator(tax_values)
                serialized_grouping_key = _serialize_python_dictionary(grouping_key)

                # Add to invoice line global tax amounts.
                if serialized_grouping_key not in invoice_global_tax_details['invoice_line_tax_details'][invoice_line]:
                    invoice_line_global_tax_details = invoice_global_tax_details['invoice_line_tax_details'][invoice_line]
                    invoice_line_global_tax_details.update({
                        'base_amount': invoice_line.balance,
                        'base_amount_currency': invoice_line.amount_currency,
                    })
                else:
                    invoice_line_global_tax_details = invoice_global_tax_details['invoice_line_tax_details'][invoice_line]

                self._add_edi_tax_values(invoice_global_tax_details, grouping_key, serialized_grouping_key, tax_values)
                self._add_edi_tax_values(invoice_line_global_tax_details, grouping_key, serialized_grouping_key, tax_values)

        return invoice_global_tax_details

    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is to prepare values in order to export an invoice through the EDI system.
        This includes the computation of the tax details for each invoice line that could be very difficult to
        handle regarding the computation of the base amount.
        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        res = {
            'record': self,
            'balance_multiplicator': -1 if self.is_inbound() else 1,
            'invoice_line_vals_list': [],
        }

        # Invoice lines details.
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda line: not line.display_type), start=1):
            line_vals = line._prepare_edi_vals_to_export()
            line_vals['index'] = index
            res['invoice_line_vals_list'].append(line_vals)

        # Totals.
        res.update({
            'total_price_subtotal_before_discount': sum(x['price_subtotal_before_discount'] for x in res['invoice_line_vals_list']),
            'total_price_discount': sum(x['price_discount'] for x in res['invoice_line_vals_list']),
        })

        return res

    def _update_payments_edi_documents(self):
        ''' Update the edi documents linked to the current journal entries. These journal entries must be linked to an
        account.payment of an account.bank.statement.line. This additional method is needed because the payment flow is
        not the same as the invoice one. Indeed, the edi documents must be updated when the reconciliation with some
        invoices is changing.
        '''
        edi_document_vals_list = []
        for payment in self:
            edi_formats = payment._get_reconciled_invoices().journal_id.edi_format_ids + payment.edi_document_ids.edi_format_id
            edi_formats = self.env['account.edi.format'].browse(edi_formats.ids) # Avoid duplicates
            for edi_format in edi_formats:
                existing_edi_document = payment.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)

                if edi_format._is_required_for_payment(payment):
                    if existing_edi_document:
                        existing_edi_document.write({
                            'state': 'to_send',
                            'error': False,
                            'blocking_level': False,
                        })
                    else:
                        edi_document_vals_list.append({
                            'edi_format_id': edi_format.id,
                            'move_id': payment.id,
                            'state': 'to_send',
                        })
                elif existing_edi_document:
                    existing_edi_document.write({
                        'state': False,
                        'error': False,
                        'blocking_level': False,
                    })

        self.env['account.edi.document'].create(edi_document_vals_list)
        self.edi_document_ids._process_documents_no_web_services()

    def _post(self, soft=True):
        # OVERRIDE
        # Set the electronic document to be posted and post immediately for synchronous formats.
        posted = super()._post(soft=soft)

        edi_document_vals_list = []
        for move in posted:
            for edi_format in move.journal_id.edi_format_ids:
                is_edi_needed = move.is_invoice(include_receipts=False) and edi_format._is_required_for_invoice(move)

                if is_edi_needed:
                    errors = edi_format._check_move_configuration(move)
                    if errors:
                        raise UserError(_("Invalid invoice configuration:\n\n%s") % '\n'.join(errors))

                    existing_edi_document = move.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)
                    if existing_edi_document:
                        existing_edi_document.write({
                            'state': 'to_send',
                            'attachment_id': False,
                        })
                    else:
                        edi_document_vals_list.append({
                            'edi_format_id': edi_format.id,
                            'move_id': move.id,
                            'state': 'to_send',
                        })

        self.env['account.edi.document'].create(edi_document_vals_list)
        posted.edi_document_ids._process_documents_no_web_services()
        return posted

    def button_cancel(self):
        # OVERRIDE
        # Set the electronic document to be canceled and cancel immediately for synchronous formats.
        res = super().button_cancel()

        self.edi_document_ids.filtered(lambda doc: doc.attachment_id).write({'state': 'to_cancel', 'error': False, 'blocking_level': False})
        self.edi_document_ids.filtered(lambda doc: not doc.attachment_id).write({'state': 'cancelled', 'error': False, 'blocking_level': False})
        self.edi_document_ids._process_documents_no_web_services()

        return res

    def button_draft(self):
        # OVERRIDE
        for move in self:
            if move.edi_show_cancel_button:
                raise UserError(_(
                    "You can't edit the following journal entry %s because an electronic document has already been "
                    "sent. Please use the 'Request EDI Cancellation' button instead."
                ) % move.display_name)

        res = super().button_draft()

        self.edi_document_ids.write({'state': False, 'error': False, 'blocking_level': False})

        return res

    def button_cancel_posted_moves(self):
        '''Mark the edi.document related to this move to be canceled.
        '''
        to_cancel_documents = self.env['account.edi.document']
        for move in self:
            is_move_marked = False
            for doc in move.edi_document_ids:
                if doc.edi_format_id._needs_web_services() \
                        and doc.attachment_id \
                        and doc.state == 'sent' \
                        and move.is_invoice(include_receipts=True) \
                        and doc.edi_format_id._is_required_for_invoice(move):
                    to_cancel_documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A cancellation of the EDI has been requested."))

        to_cancel_documents.write({'state': 'to_cancel', 'error': False, 'blocking_level': False})

    def _get_edi_document(self, edi_format):
        return self.edi_document_ids.filtered(lambda d: d.edi_format_id == edi_format)

    def _get_edi_attachment(self, edi_format):
        return self._get_edi_document(edi_format).attachment_id

    ####################################################
    # Import Electronic Document
    ####################################################

    def _get_create_invoice_from_attachment_decoders(self):
        # OVERRIDE
        res = super()._get_create_invoice_from_attachment_decoders()
        res.append((10, self.env['account.edi.format'].search([])._create_invoice_from_attachment))
        return res

    def _get_update_invoice_from_attachment_decoders(self, invoice):
        # OVERRIDE
        res = super()._get_update_invoice_from_attachment_decoders(invoice)
        res.append((10, self.env['account.edi.format'].search([])._update_invoice_from_attachment))
        return res

    ####################################################
    # Business operations
    ####################################################

    def action_process_edi_web_services(self):
        docs = self.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        if 'blocking_level' in self.env['account.edi.document']._fields:
            docs = docs.filtered(lambda d: d.blocking_level != 'error')
        docs._process_documents_web_services(with_commit=False)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ####################################################
    # Export Electronic Document
    ####################################################

    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is the same as '_prepare_edi_vals_to_export' but for a single invoice line.
        This includes the computation of the tax details for each invoice line or the management of the discount.
        Indeed, in some EDI, we need to provide extra values depending the discount such as:
        - the discount as an amount instead of a percentage.
        - the price_unit but after subtraction of the discount.
        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        if self.discount == 100.0:
            gross_price_subtotal = self.currency_id.round(self.price_unit * self.quantity)
        else:
            gross_price_subtotal = self.currency_id.round(self.price_subtotal / (1 - self.discount / 100.0))

        res = {
            'line': self,
            'price_unit_after_discount': self.currency_id.round(self.price_unit * (1 - (self.discount / 100.0))),
            'price_subtotal_before_discount': gross_price_subtotal,
            'price_subtotal_unit': self.currency_id.round(self.price_subtotal / self.quantity) if self.quantity else 0.0,
            'price_total_unit': self.currency_id.round(self.price_total / self.quantity) if self.quantity else 0.0,
            'price_discount': gross_price_subtotal - self.price_subtotal,
            'price_discount_unit': (gross_price_subtotal - self.price_subtotal) / self.quantity if self.quantity else 0.0,
            'gross_price_total_unit': self.currency_id.round(gross_price_subtotal / self.quantity) if self.quantity else 0.0,
            'unece_uom_code': self.product_id.product_tmpl_id.uom_id._get_unece_code(),
        }
        return res

    def reconcile(self):
        # OVERRIDE
        # In some countries, the payments must be sent to the government under some condition. One of them could be
        # there is at least one reconciled invoice to the payment. Then, we need to update the state of the edi
        # documents during the reconciliation.
        all_lines = self + self.matched_debit_ids.debit_move_id + self.matched_credit_ids.credit_move_id
        payments = all_lines.move_id.filtered(lambda move: move.payment_id or move.statement_line_id)

        invoices_per_payment_before = {pay: pay._get_reconciled_invoices() for pay in payments}
        res = super().reconcile()
        invoices_per_payment_after = {pay: pay._get_reconciled_invoices() for pay in payments}

        changed_payments = self.env['account.move']
        for payment, invoices_after in invoices_per_payment_after.items():
            invoices_before = invoices_per_payment_before[payment]

            if set(invoices_after.ids) != set(invoices_before.ids):
                changed_payments |= payment
        changed_payments._update_payments_edi_documents()

        return res

    def remove_move_reconcile(self):
        # OVERRIDE
        # When a payment has been sent to the government, it usually contains some information about reconciled
        # invoices. If the user breaks a reconciliation, the related payments must be cancelled properly and then, a new
        # electronic document must be generated.
        all_lines = self + self.matched_debit_ids.debit_move_id + self.matched_credit_ids.credit_move_id
        payments = all_lines.move_id.filtered(lambda move: move.payment_id or move.statement_line_id)

        invoices_per_payment_before = {pay: pay._get_reconciled_invoices() for pay in payments}
        res = super().remove_move_reconcile()
        invoices_per_payment_after = {pay: pay._get_reconciled_invoices() for pay in payments}

        changed_payments = self.env['account.move']
        for payment, invoices_after in invoices_per_payment_after.items():
            invoices_before = invoices_per_payment_before[payment]

            if set(invoices_after.ids) != set(invoices_before.ids):
                changed_payments |= payment
        changed_payments._update_payments_edi_documents()

        return res
