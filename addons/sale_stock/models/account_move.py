from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import formatLang

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("line_ids.sale_line_ids.order_id.incoterm_location")
    def _compute_incoterm_location(self):
        super()._compute_incoterm_location()

    def _get_order_incoterm_locations(self):
        return [
            *super()._get_order_incoterm_locations(),
            *self.line_ids.sale_line_ids.order_id.mapped("incoterm_location"),
        ]

    @api.depends("line_ids.sale_line_ids.order_id.date_effective")
    def _compute_delivery_date(self):
        super()._compute_delivery_date()
        for move in self:
            sale_order_date_effective = list(
                filter(
                    None,
                    move.line_ids.sale_line_ids.order_id.mapped("date_effective"),
                ),
            )
            date_effective_res = (
                max(sale_order_date_effective) if sale_order_date_effective else False
            )
            if date_effective_res:
                _debug.logic("delivery_date_from_order", move=move, by="date_effective")
                move.delivery_date = fields.Datetime.context_timestamp(
                    move, date_effective_res
                )

    def _get_anglo_saxon_price_ctx(self):
        ctx = super()._get_anglo_saxon_price_ctx()
        move_is_downpayment = self.invoice_line_ids.filtered(
            lambda line: any(line.sale_line_ids.mapped("is_downpayment")),
        )
        return dict(ctx, move_is_downpayment=move_is_downpayment)

    def _prepare_invoice_lot_rows(self):
        self.check_singleton()

        res = super()._prepare_invoice_lot_rows()

        if (
            self.state == "draft"
            or not self.invoice_date
            or self.move_type not in ("out_invoice", "out_refund")
        ):
            _debug.logic("invoiced_lots_skipped", move=self, reason="not_posted")
            return res

        current_invoice_amls = self.invoice_line_ids.filtered(
            lambda aml: (
                aml.display_type == "product"
                and aml.product_id
                and aml.product_id.type == "consu"
                and aml.quantity
            ),
        )
        all_invoices_amls = (
            current_invoice_amls.sale_line_ids.invoice_line_ids.filtered(
                lambda aml: aml._filter_aml_lot_valuation()
            ).sorted(lambda aml: (aml.date, aml.move_name, aml.id))
        )
        index = (
            all_invoices_amls.ids.index(current_invoice_amls[:1].id)
            if current_invoice_amls[:1] in all_invoices_amls
            else 0
        )
        previous_amls = all_invoices_amls[:index]
        invoiced_qties = current_invoice_amls._get_invoiced_qty_per_product()
        invoiced_products = invoiced_qties.keys()

        if self.move_type == "out_invoice":
            previous_amls = previous_amls.filtered(
                lambda aml: aml.move_id.payment_state != "reversed",
            )

        previous_qties_invoiced = previous_amls._get_invoiced_qty_per_product()

        if self.move_type == "out_refund":
            for p in previous_qties_invoiced:
                previous_qties_invoiced[p] = -previous_qties_invoiced[p]
            for p in invoiced_qties:
                invoiced_qties[p] = -invoiced_qties[p]

        qties_per_lot = defaultdict(float)
        previous_qties_delivered = defaultdict(float)
        stock_move_lines = (
            current_invoice_amls.sale_line_ids.move_ids.move_line_ids.filtered(
                lambda sml: sml.state == "done" and sml.lot_id,
            ).sorted(lambda sml: (sml.date, sml.id))
        )
        for sml in stock_move_lines:
            if (
                sml.product_id not in invoiced_products
                or not sml._is_lot_display_in_invoice_required()
            ):
                continue

            product = sml.product_id
            product_uom_id = product.uom_id
            quantity = sml.product_uom_id._get_quantity_in_unit(
                sml.quantity, product_uom_id
            )

            is_stock_return = (
                self.move_type == "out_invoice"
                and sml.location_id.usage == "customer"
                and sml.location_dest_id.usage in ("internal", "supplier")
            ) or (
                self.move_type == "out_refund"
                and sml.location_dest_id.usage == "customer"
                and sml.location_id.usage in ("internal", "supplier")
            )

            if is_stock_return:
                returned_qty = min(qties_per_lot[sml.lot_id], quantity)
                qties_per_lot[sml.lot_id] -= returned_qty
                quantity = returned_qty - quantity

            previous_qty_invoiced = previous_qties_invoiced[product]
            previous_qty_transferred = previous_qties_delivered[product]
            if (
                product_uom_id.compare(quantity, 0) < 0
                or product_uom_id.compare(
                    previous_qty_transferred, previous_qty_invoiced
                )
                < 0
            ):
                previously_done = (
                    quantity
                    if is_stock_return
                    else min(previous_qty_invoiced - previous_qty_transferred, quantity)
                )
                previous_qties_delivered[product] += previously_done
                quantity -= previously_done

            qties_per_lot[sml.lot_id] += quantity

        _debug.perf.count("invoiced_lots", move=self, lots=len(qties_per_lot))
        for lot, qty in qties_per_lot.items():
            lot = lot.sudo()

            if (
                lot.product_uom_id.is_zero(invoiced_qties[lot.product_id])
                or lot.product_uom_id.compare(qty, 0) <= 0
            ):
                continue

            invoiced_lot_qty = min(qty, invoiced_qties[lot.product_id])
            invoiced_qties[lot.product_id] -= invoiced_lot_qty
            res.append(
                {
                    "product_name": lot.product_id.display_name,
                    "quantity": formatLang(
                        self.env, invoiced_lot_qty, dp="Product Unit"
                    ),
                    "uom_name": lot.product_uom_id.name,
                    "lot_name": lot.name,
                    "lot_id": lot.id,
                },
            )

        return res

    def _get_field_protections(self, vals, records):
        res = super()._get_field_protections(vals, records)
        perma_protected = {self._fields["delivery_date"]}

        if records._name == self._name:
            res.append((perma_protected, records))
        elif records._name == self.line_ids._name:
            res.append((perma_protected, records.move_id))

        return res

    def _stock_account_get_last_step_stock_moves(self):
        rslt = super()._stock_account_get_last_step_stock_moves()
        for invoice in self:
            if invoice.move_type not in ["out_invoice", "out_refund"]:
                continue

            if invoice.move_type == "out_invoice" or (
                invoice.move_type == "out_refund"
                and any(invoice.invoice_line_ids.sale_line_ids.mapped("is_downpayment"))
            ):
                rslt += invoice.mapped(
                    "invoice_line_ids.sale_line_ids.move_ids",
                ).filtered(
                    lambda x: (
                        x.state == "done" and x.location_dest_id.usage == "customer"
                    ),
                )
            else:
                rslt += invoice.mapped(
                    "reversed_entry_id.invoice_line_ids.sale_line_ids.move_ids"
                ).filtered(
                    lambda x: x.state == "done" and x.location_id.usage == "customer",
                )
                rslt += invoice.mapped(
                    "invoice_line_ids.sale_line_ids.move_ids",
                ).filtered(
                    lambda x: x.state == "done" and x.location_id.usage == "customer",
                )

        return rslt
