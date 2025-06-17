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
        inverse_name='pos_order_id',
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
        compute='_compute_l10n_es_edi_verifactu_state', store=True,
        help="""- Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent document
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
    )
    l10n_es_edi_verifactu_error_level = fields.Selection(
        string="Veri*Factu Error Level",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
        ],
        compute="_compute_l10n_es_edi_verifactu_errors_and_error_level",
    )
    l10n_es_edi_verifactu_errors = fields.Html(
        string="Veri*Factu Errors",
        compute="_compute_l10n_es_edi_verifactu_errors_and_error_level",
    )
    l10n_es_edi_verifactu_qr_code = fields.Char(
        string="Veri*Factu QR Code",
        compute='_compute_l10n_es_edi_verifactu_qr_code',
    )
    l10n_es_edi_verifactu_show_cancel_button = fields.Boolean(
        string="Show Veri*Factu Cancel Button",
        compute='_compute_l10n_es_edi_verifactu_show_cancel_button',
    )
    l10n_es_edi_verifactu_refund_reason = fields.Selection(
        selection=[
            ('R1', "R1: Art 80.1 and 80.2 and error of law"),
            ('R2', "R2: Art. 80.3"),
            ('R3', "R3: Art. 80.4"),
            ('R4', "R4: Rest"),
            ('R5', "R5: Corrective invoices concerning simplified invoices"),
        ],
        string="Veri*Factu Refund Reason",
        copy=False,
    )

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        for order in self:
            order.l10n_es_edi_verifactu_required = order.country_code == 'ES' and order.company_id.l10n_es_edi_verifactu_required

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state', 'l10n_es_edi_verifactu_document_ids.errors')
    def _compute_l10n_es_edi_verifactu_errors_and_error_level(self):
        for order in self:
            last_document = order.l10n_es_edi_verifactu_document_ids.sorted()[:1]
            error_level = False if last_document.state == 'accepted' else last_document.state
            order.l10n_es_edi_verifactu_error_level = error_level
            order.l10n_es_edi_verifactu_errors = last_document.errors

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.state')
    def _compute_l10n_es_edi_verifactu_state(self):
        for order in self:
            state = order.l10n_es_edi_verifactu_document_ids._get_state()
            order.l10n_es_edi_verifactu_state = state

    @api.depends('l10n_es_edi_verifactu_document_ids', 'l10n_es_edi_verifactu_document_ids.record_identifier')
    def _compute_l10n_es_edi_verifactu_qr_code(self):
        for order in self:
            invoice = order.account_move
            if invoice:
                url = invoice.l10n_es_edi_verifactu_qr_code
            else:
                last_submission = order.l10n_es_edi_verifactu_document_ids._get_last('submission')
                url = last_submission._get_qr_code_img_url() if last_submission else False
            order.l10n_es_edi_verifactu_qr_code = url

    @api.depends('l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_show_cancel_button(self):
        for order in self:
            order.l10n_es_edi_verifactu_show_cancel_button = order.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')

    @api.model
    def l10n_es_edi_verifactu_get_refund_reason_selection(self):
        return self._fields['l10n_es_edi_verifactu_refund_reason']._description_selection(self.env)

    def l10n_es_edi_verifactu_button_cancel(self):
        self._l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)

    def l10n_es_edi_verifactu_button_send(self):
        self._l10n_es_edi_verifactu_mark_for_next_batch()

    def _l10n_es_edi_verifactu_check(self, cancellation=False):
        self.ensure_one()
        errors = []

        if self.state != 'paid':
            errors.append(_("Veri*Factu documents can only be generated for paid Point of Sale Orders."))

        return errors

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()

        company = self.company_id
        document_type = 'cancellation' if cancellation else 'submission'
        vals = {
            'company': company,
            'record': self,
            'cancellation': cancellation,
            'errors': self._l10n_es_edi_verifactu_check(cancellation=cancellation),
            'document_vals': {
                'pos_order_id': self.id,
                'company_id': company.id,
                'document_type': document_type,
            },
        }

        if vals['errors']:
            return vals

        company_in_simplified_regime = company.l10n_es_edi_verifactu_special_vat_regime == 'simplified'

        documents = self.l10n_es_edi_verifactu_document_ids
        # Just checking whether the last document was rejected is enough; we do not allow to submit the same record
        # again after a cancellation (else we get the error '[3000] Registro de facturación duplicado.').
        rejected_before = documents._get_last(document_type).state == 'rejected'
        refunded_order = self.refunded_order_ids  # it is max 1 record (see `create_from_ui`)

        vals.update({
            'rejected_before': rejected_before,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
            'delivery_date': False,
            'description': None,
            'invoice_date': self.date_order.date(),
            'is_simplified': True,
            # NOTE: invoice with negative amounts possible (when no `refunded_order` specified)
            'move_type': 'out_refund' if refunded_order else 'out_invoice',
            'verifactu_move_type': 'correction_incremental' if refunded_order else 'invoice',
            'name': self.name,
            'partner': self.partner_id.commercial_partner_id,
            'refund_reason': self.l10n_es_edi_verifactu_refund_reason,
            'refunded_document': refunded_order.l10n_es_edi_verifactu_document_ids._get_last('submission'),
            'substituted_document': None,
            'substituted_document_reversal_document': None,
            'documents': documents,
            'record_identifier': documents._get_last('submission').record_identifier,
            # TODO: check
            'verifactu_tax_type': '01',
            'clave_regimen': '20' if company_in_simplified_regime else '01',
        })

        tax_details_functions = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_details_functions(company)

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

        vals['errors'] = self.env['l10n_es_edi_verifactu.document']._check_record_values(vals)

        return vals

    def _l10n_es_edi_verifactu_create_document(self, cancellation=False, previous_record_identifier=None):
        self.ensure_one()

        record_values = self._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)

        return self.env['l10n_es_edi_verifactu.document']._create_for_record(
            record_values, previous_record_identifier=previous_record_identifier,
        )

    def _l10n_es_edi_verifactu_mark_for_next_batch(self, cancellation=False):
        record_values_list = [
            order._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)
            for order in self
        ]
        return self.env['l10n_es_edi_verifactu.document']._mark_records_for_next_batch(record_values_list)

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

    def _export_for_ui(self, order):
        # EXTENDS 'point_of_sale'
        vals = super()._export_for_ui(order)
        vals['l10n_es_edi_verifactu_refund_reason'] = order.l10n_es_edi_verifactu_refund_reason
        return vals

    def _order_fields(self, ui_order):
        # EXTENDS 'point_of_sale'
        vals = super()._order_fields(ui_order)
        vals['l10n_es_edi_verifactu_refund_reason'] = ui_order.get('l10n_es_edi_verifactu_refund_reason', False)
        return vals

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
                if refunded_order and not self.l10n_es_edi_verifactu_refund_reason:
                    raise UserError(_("You have to specify a refund reason."))
                if self.to_invoice and refunded_order.state != 'invoiced':
                    raise UserError(_("You cannot invoice a refund whose linked order hasn't been invoiced."))
                if not self.to_invoice and refunded_order.state == 'invoiced':
                    raise UserError(_("Please invoice the refund as the linked order has been invoiced."))

        return super()._process_saved_order(draft)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()

        if self.l10n_es_edi_verifactu_required and not self.to_invoice:
            self._l10n_es_edi_verifactu_mark_for_next_batch()

        return res

    def _generate_pos_order_invoice(self):
        res = super()._generate_pos_order_invoice()

        for order in self:
            waiting_documents = order.l10n_es_edi_verifactu_document_ids._filter_waiting()
            if waiting_documents:
                raise UserError(_("The order can not be invoiced. It is waiting to send a Veri*Factu record to the AEAT already."))

            # Cancel the order
            if order.l10n_es_edi_verifactu_state in ('accepted', 'registered_with_errors'):
                order._l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)

            refunded_order = self.refunded_order_ids
            if refunded_order and not refunded_order.account_move:
                raise UserError(_("The order can not be invoiced. The refunded order needs to be invoiced first."))

            # Register the invoice instead. The call to `super()` may already have sent it
            invoice = order.account_move
            if invoice.l10n_es_edi_verifactu_required and invoice and not invoice.l10n_es_edi_verifactu_document_ids:
                invoice._l10n_es_edi_verifactu_mark_for_next_batch()

        return res

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        res['l10n_es_edi_verifactu_refund_reason'] = self.l10n_es_edi_verifactu_refund_reason
        return res
