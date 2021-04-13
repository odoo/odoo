# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EdiMixin(models.AbstractModel):
    _name = 'edi.mixin'

    edi_document_ids = fields.Many2many(
        comodel_name='edi.document', store=False) # to be inherited then with different store=True
    edi_state = fields.Selection(
        selection=[('to_send', 'To Send'), ('sent', 'Sent'), ('to_cancel', 'To Cancel'), ('cancelled', 'Cancelled')],
        string="Electronic invoicing",
        store=True,
        compute='_compute_edi_state',
        help='The aggregated state of all the EDIs with web-service of this move')
    edi_error_count = fields.Integer(
        compute='_compute_edi_error_count',
        help='How many EDIs are in error for this move ?')
    edi_blocking_level = fields.Selection(
        selection=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
        compute='_compute_edi_error_message')
    edi_error_message = fields.Html(
        compute='_compute_edi_error_message')
    edi_web_services_to_process = fields.Text(
        compute='_compute_edi_web_services_to_process',
        help="Technical field to display the documents that will be processed by the CRON")
    edi_show_cancel_button = fields.Boolean(
        compute='_compute_edi_show_cancel_button')
    edi_show_abandon_cancel_button = fields.Boolean(
        compute='_compute_edi_show_abandon_cancel_button')

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

    @api.depends('edi_error_count', 'edi_document_ids.error', 'edi_document_ids.blocking_level')
    def _compute_edi_error_message(self):
        for move in self:
            if move.edi_error_count == 0:
                move.edi_error_message = None
                move.edi_blocking_level = None
            elif move.edi_error_count == 1:
                error_doc = move.edi_document_ids.filtered(lambda d: d.error)
                move.edi_error_message = error_doc.error
                move.edi_blocking_level = error_doc.blocking_level
            else:
                error_levels = set([doc.blocking_level for doc in move.edi_document_ids])
                if 'error' in error_levels:
                    move.edi_error_message = str(move.edi_error_count) + _(" Electronic invoicing error(s)")
                    move.edi_blocking_level = 'error'
                elif 'warning' in error_levels:
                    move.edi_error_message = str(move.edi_error_count) + _(" Electronic invoicing warning(s)")
                    move.edi_blocking_level = 'warning'
                else:
                    move.edi_error_message = str(move.edi_error_count) + _(" Electronic invoicing info(s)")
                    move.edi_blocking_level = 'info'

    @api.depends(
        'edi_document_ids',
        'edi_document_ids.state',
        'edi_document_ids.blocking_level',
        'edi_document_ids.edi_format_id',
        'edi_document_ids.edi_format_id.name')
    def _compute_edi_web_services_to_process(self):
        for move in self:
            to_process = move.edi_document_ids.filtered(lambda d: d.state in ['to_send', 'to_cancel'] and d.blocking_level != 'error')
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
                                               and doc.edi_format_id._is_required_for_invoice(move)
                                              for doc in move.edi_document_ids])

    @api.depends(
        'state',
        'edi_document_ids.state',
        'edi_document_ids.attachment_id')
    def _compute_edi_show_abandon_cancel_button(self):
        for move in self:
            move.edi_show_abandon_cancel_button = any(doc.edi_format_id._needs_web_services()
                                                      and doc.state == 'to_cancel'
                                                      and doc.edi_format_id._is_required_for_invoice(move)
                                                      for doc in move.edi_document_ids)

    ####################################################
    # Export Electronic Document
    ####################################################

    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is to prepare values in order to export an invoice through the EDI system.
        This includes the computation of the tax details for each invoice line that could be very difficult to
        handle regarding the computation of the base amount.

        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        def convert(amount):
            return self.currency_id._convert(amount, self.company_currency_id, self.company_id, self.date)

        res = {
            'record': self,
            'invoice_line_vals_list': [],
        }

        # Invoice lines details.
        tax_detail_per_tax = {}
        added_base_amount_keys = set()
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda line: not line.display_type), start=1):
            line_vals = line._prepare_edi_vals_to_export()
            line_vals['index'] = index
            res['invoice_line_vals_list'].append(line_vals)

            # Tax details.
            for tax_vals in line_vals['tax_detail_vals_list']:
                tax_detail_per_tax.setdefault(tax_vals['tax'], {
                    'tax': tax_vals['tax'],
                    'orig_tax': tax_vals['orig_tax'],
                    'tax_base_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'tax_amount_currency': 0.0,
                    'tax_amount_closing': 0.0,
                    'tax_amount_currency_closing': 0.0,
                    'tag_ids': set(),
                })
                vals = tax_detail_per_tax[tax_vals['tax']]

                # Avoid adding multiple times the same base (e.g. with multiple taxes on the same line or multiple
                # repartition lines).
                base_amount_key = (line.id, tax_vals['tax']['id'])
                if base_amount_key not in added_base_amount_keys:
                    vals['tax_base_amount_currency'] += tax_vals['tax_base_amount_currency']
                    added_base_amount_keys.add(base_amount_key)

                vals['tax_amount_currency'] += tax_vals['tax_amount_currency']
                vals['tax_amount_currency_closing'] += tax_vals['tax_amount_currency_closing']
                for tag in tax_vals['tags']:
                    vals['tag_ids'].add(tag.id)

        # Format the aggregated tax details as a list.
        res['tax_detail_vals_list'] = []
        for tax_detail_vals in tax_detail_per_tax.values():
            res['tax_detail_vals_list'].append({
                **tax_detail_vals,
                'tags': self.env['account.account.tag'].browse(tax_detail_vals['tag_ids']),
                'tax_base_amount': convert(tax_detail_vals['tax_base_amount_currency']),
                'tax_amount': convert(tax_detail_vals['tax_amount_currency']),
                'tax_amount_closing': convert(tax_detail_vals['tax_amount_currency_closing']),
            })

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
            edi_formats = self.env['edi.format'].browse(edi_formats.ids) # Avoid duplicates
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

        self.env['edi.document'].create(edi_document_vals_list)
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

        self.env['edi.document'].create(edi_document_vals_list)
        posted.edi_document_ids._process_documents_no_web_services()
        self.env.ref('account_edi.ir_cron_edi_network')._trigger()
        return posted

    def button_cancel(self):
        # OVERRIDE
        # Set the electronic document to be canceled and cancel immediately for synchronous formats.
        res = super().button_cancel()

        self.edi_document_ids.filtered(lambda doc: doc.attachment_id).write({'state': 'to_cancel', 'error': False, 'blocking_level': False})
        self.edi_document_ids.filtered(lambda doc: not doc.attachment_id).write({'state': 'cancelled', 'error': False, 'blocking_level': False})
        self.edi_document_ids._process_documents_no_web_services()
        self.env.ref('account_edi.ir_cron_edi_network')._trigger()

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
        to_cancel_documents = self.env['edi.document']
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

    def button_abandon_cancel_posted_posted_moves(self):
        '''Cancel the request for cancellation of the EDI.
        '''
        documents = self.env['edi.document']
        for move in self:
            is_move_marked = False
            for doc in move.edi_document_ids:
                if doc.state == 'to_cancel' \
                        and move.is_invoice(include_receipts=True) \
                        and doc.edi_format_id._is_required_for_invoice(move):
                    documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A request for cancellation of the EDI has been called off."))

        documents.write({'state': 'sent'})

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
        res.append((10, self.env['edi.format'].search([])._create_invoice_from_attachment))
        return res

    def _get_update_invoice_from_attachment_decoders(self, invoice):
        # OVERRIDE
        res = super()._get_update_invoice_from_attachment_decoders(invoice)
        res.append((10, self.env['edi.format'].search([])._update_invoice_from_attachment))
        return res

    ####################################################
    # Business operations
    ####################################################

    def action_process_edi_web_services(self):
        docs = self.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
        docs._process_documents_web_services()

    def action_retry_edi_documents_error(self):
        self.edi_document_ids.write({'error': False, 'blocking_level': False})
        self.action_process_edi_web_services()
