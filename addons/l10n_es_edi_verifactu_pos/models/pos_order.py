from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'l10n_es_edi_verifactu.record_mixin']

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        # Overrides verifactu_record_mixin.py
        for order in self:
            order.l10n_es_edi_verifactu_required = order.country_code == 'ES'

    @api.depends('company_id', 'name', 'date_order', 'amount_total')
    def _compute_l10n_es_edi_verifactu_record_identifier(self):
        for order in self:
            if not order.l10n_es_edi_verifactu_required:
                identifier = False
            elif order.state == 'draft':
                identifier = {
                    'errors': [_("The Point of Sale Order is in draft.")]
                }
            else:
                identifier = self.env['l10n_es_edi_verifactu.document']._record_identifier(
                    order.company_id, order.name, order.date_order, order.amount_total
                )
            order.l10n_es_edi_verifactu_record_identifier = identifier

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()
        errors = []

        record_identifier = self.l10n_es_edi_verifactu_record_identifier
        errors.extend(record_identifier['errors'])

        company = self.company_id

        vals = {
            'cancellation': cancellation,
            'company': company,
            'delivery_date': False,
            'description': None,
            'identifier': record_identifier,
            'invoice_date': self.date_order,
            'is_simplified': True,
            'move_type': 'out_invoice' if self.amount_total >= 0 else 'out_refund',
            'name': self.name,
            'partner': self.partner_id.address_get(['invoice'])['invoice'],
            'record': self,
            'rejected_before': False,  # TODO:
            'refunded_record': self.refunded_order_ids,
            'verifactu_state': self.l10n_es_edi_verifactu_state,
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
        # Extend 'point_of_sale' to ensure len(order.refunded_order_ids) <= 1 for any created Veri*Factu order (like in 17.1+)
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
            if not self.to_invoice and self.amount_total > self.config_id.l10n_es_simplified_invoice_limit:
                raise UserError(self.env._("Please create an invoice for an amount over %s.", self.company_id.l10n_es_simplified_invoice_limit))
            refunded_order = self.refunded_order_ids
            if len(refunded_order) > 1:
                raise UserError(self.env._("You can only refund products from the same order."))
            if refunded_order:
                if self.to_invoice and refunded_order.state != 'invoiced':
                    raise UserError(self.env._("You cannot invoice a refund whose linked order hasn't been invoiced."))
                if not self.to_invoice and refunded_order.state == 'invoiced':
                    raise UserError(self.env._("Please invoice the refund as the linked order has been invoiced."))

        return super()._process_saved_order(draft)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()

        if self.l10n_es_edi_verifactu_required and not self.to_invoice:
            self.l10n_es_edi_verifactu_mark_for_next_batch()

        return res

    def _generate_pos_order_invoice(self):
        res = super()._generate_pos_order_invoice()

        for order in self:
            invoice = order.account_move
            if order.l10n_es_edi_verifactu_state in ('accepted', 'registered_with_errors'):
                order.l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)
            if invoice.l10n_es_edi_verifactu_required and invoice and not invoice.l10n_es_edi_verifactu_record_document_ids:
                invoice.l10n_es_edi_verifactu_mark_for_next_batch()

        return res

    def l10n_es_edi_verifactu_button_send(self):
        self.l10n_es_edi_verifactu_mark_for_next_batch()
