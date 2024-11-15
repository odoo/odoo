from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        compute='_compute_l10n_es_edi_verifactu_required',
    )
    l10n_es_edi_verifactu_document_ids = fields.One2many(
        comodel_name='l10n_es_edi_verifactu.document',
        inverse_name='res_id',
        string="Veri*Factu Documents",
    )
    l10n_es_edi_verifactu_state = fields.Selection(
        string="Veri*Factu Status",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
            ('accepted', "Accepted"),
            ('cancelled', "Cancelled"),
        ],
        compute='_compute_l10n_es_edi_verifactu_info_from_document_ids',
        help="""- Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent document
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
        store=True,
    )
    l10n_es_edi_verifactu_last_erroneous_document_id = fields.Many2one(
        comodel_name='l10n_es_edi_verifactu.document',
        compute='_compute_l10n_es_edi_verifactu_info_from_document_ids',
        string="Last Erroneous Veri*Factu Document",
        help="This QR code is mandatory for Veri*Factu invoices.",
        store=True,
    )
    l10n_es_edi_verifactu_error_level = fields.Selection(
        string="Veri*Factu Error Level",
        related="l10n_es_edi_verifactu_last_erroneous_document_id.state",
        store=True,
    )
    l10n_es_edi_verifactu_errors = fields.Html(
        string="Veri*Factu Errors",
        related="l10n_es_edi_verifactu_last_erroneous_document_id.errors",
    )
    l10n_es_edi_verifactu_qr_code = fields.Char(
        string="Veri*Factu QR Code",
        compute='_compute_l10n_es_edi_verifactu_qr_code',
        help="This QR code is mandatory for Veri*Factu invoices.",
    )
    l10n_es_edi_verifactu_show_cancel_button = fields.Boolean(
        string="Show Veri*Factu Cancel Button",
        compute='_compute_l10n_es_edi_verifactu_show_cancel_button',
    )

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        for order in self:
            order.l10n_es_edi_verifactu_required = order.country_code == 'ES' and order.company_id.l10n_es_edi_verifactu_required

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_l10n_es_edi_verifactu_info_from_document_ids(self):
        for record in self:
            documents_info = self.env['l10n_es_edi_verifactu.document']._analyze_record_documents(record)
            record.l10n_es_edi_verifactu_last_erroneous_document_id = documents_info['last_erroneous_document']
            record.l10n_es_edi_verifactu_state = documents_info['state']

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.record_identifier')
    def _compute_l10n_es_edi_verifactu_qr_code(self):
        for record in self:
            url = self.env['l10n_es_edi_verifactu.document']._get_qr_code_img_url(record)
            record.l10n_es_edi_verifactu_qr_code = url

    @api.depends('l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_show_cancel_button(self):
        for move in self:
            move.l10n_es_edi_verifactu_show_cancel_button = move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')

    def l10n_es_edi_verifactu_button_cancel(self):
        created_documents = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(self, cancellation=True)
        skipped_moves = self.filtered(lambda move: not created_documents.get(move))
        if skipped_moves and len(self) == 1:
            raise UserError(_("We are waiting to send a Veri*Factu record to the AEAT already."))
        # In other cases we just silently skip them

    def _l10n_es_edi_verifactu_record_identifier(self):
        invoice = self.account_move
        if invoice:
            return invoice._l10n_es_edi_verifactu_record_identifier()

        last_submission_document = self.l10n_es_edi_verifactu_document_ids.filtered(
            lambda rd: rd.document_type == 'submission'
        ).sorted()[:1]
        return last_submission_document.record_identifier

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'paid':
            errors.append(_("Veri*Factu documents can only be generated for paid Point of Sale Orders."))
            return {}, errors

        documents_info = self.env['l10n_es_edi_verifactu.document']._analyze_record_documents(self)
        document_type = 'cancellation' if cancellation else 'submission'
        rejected_before = bool(documents_info[f'last_rejected_{document_type}'])

        company = self.company_id

        vals = {
            'cancellation': cancellation,
            'record': self,
            'rejected_before': rejected_before,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
            'company': company,
            'delivery_date': False,
            'description': None,
            'invoice_date': self.date_order.date(),
            'is_simplified': True,
            'move_type': 'out_invoice' if self.amount_total >= 0 else 'out_refund',
            'name': self.name,
            'partner': self.partner_id.address_get(['invoice'])['invoice'],
            'refunded_record': self.refunded_order_ids,  # it is max 1 record (see `create_from_ui`)
        }

        tax_details_functions = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_details_functions()

        base_lines = self.lines.filtered(tax_details_functions['full_filter_invl_to_apply'])._prepare_tax_base_line_values()
        taxes_values_to_aggregate = []
        for base_line in base_lines:
            # Don't consider fully discounted lines for taxes computation.
            if base_line['discount'] == 100.0:
                continue
            to_update_vals, tax_values_list = self.env['account.tax']._compute_taxes_for_single_line(base_line)
            taxes_values_to_aggregate.append((base_line, to_update_vals, tax_values_list))

        distribute_total_on_line = not company or company.tax_calculation_rounding_method != 'round_globally'
        vals['tax_details'] = self.env['account.tax']._aggregate_taxes(
            taxes_values_to_aggregate,
            filter_tax_values_to_apply=tax_details_functions['filter_to_apply'],
            grouping_key_generator=tax_details_functions['grouping_key_generator'],
            distribute_total_on_line=distribute_total_on_line,
        )

        return vals, errors

    # TODO: Remove in 17.1+
    @api.model
    def create_from_ui(self, orders, draft=False):
        # Extend 'point_of_sale' to ensure len(order.refunded_order_ids) <= 1 for any created Veri*Factu order
        # (like in 17.1+; see commit 45e90b2d9e818fcd939c5e143a162762eeebd8d3)
        for order in orders:
            if order['data'].get('l10n_es_edi_verifactu_required'):
                refunded_orderline_ids = [line[2]['refunded_orderline_id'] for line in order['data']['lines'] if line[2].get('refunded_orderline_id')]
                refunded_orders = self.env['pos.order.line'].browse(refunded_orderline_ids).mapped('order_id')
                if len(refunded_orders) > 1:
                    raise ValidationError(_("You can only refund products from the same order."))
        return super().create_from_ui(orders, draft=draft)

    def _process_saved_order(self, draft):
        self.ensure_one()
        if self.l10n_es_edi_verifactu_required:
            simplified_limit = self.config_id.l10n_es_simplified_invoice_limit
            if not self.to_invoice and self.amount_total > simplified_limit:
                raise UserError(_("Please create an invoice for an amount over %s.", simplified_limit))
            refunded_order = self.refunded_order_ids
            if len(refunded_order) > 1:
                raise UserError(_("You can only refund products from the same order."))
            if refunded_order:
                if self.to_invoice and refunded_order.state != 'invoiced':
                    raise UserError(_("You cannot invoice a refund whose linked order hasn't been invoiced."))
                if not self.to_invoice and refunded_order.state == 'invoiced':
                    raise UserError(_("Please invoice the refund as the linked order has been invoiced."))

        return super()._process_saved_order(draft)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()

        if self.l10n_es_edi_verifactu_required and not self.to_invoice:
            self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(self)

        return res

    def _generate_pos_order_invoice(self):
        res = super()._generate_pos_order_invoice()

        for order in self:
            # TODO: check / improve handling of waiting documents / sending multipled documents
            waiting_documents = order.l10n_es_edi_verifactu_document_ids.filtered(lambda rd: not rd.state)
            if waiting_documents:
                raise UserError(_("The order can not be invoiced. It is waiting to send a Veri*Factu record to the AEAT already."))

            # Cancel the order
            if order.l10n_es_edi_verifactu_state in ('accepted', 'registered_with_errors'):
                self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(order, cancellation=True)

            # Register the invoice instead. The call to `super()` may already have sent it
            invoice = order.account_move
            if invoice.l10n_es_edi_verifactu_required and invoice and not invoice.l10n_es_edi_verifactu_document_ids:
                self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(invoice)

        return res

    def l10n_es_edi_verifactu_button_send(self):
        created_documents = self.env['l10n_es_edi_verifactu.document'].mark_records_for_next_batch(self)
        skipped_orders = self.filtered(lambda order: not created_documents.get(order))
        if skipped_orders and len(self) == 1:
            raise UserError(_("The order is waiting to send a Veri*Factu record to the AEAT already."))
        # In other cases we just silently skip them
