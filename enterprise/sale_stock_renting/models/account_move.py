# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoiced_lot_values(self):
        """ Display Rental lots on invoice report when functionality is enabled. """
        res = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft':
            return res

        sale_orders = self.mapped('invoice_line_ids.sale_line_ids.order_id').filtered('is_rental_order')
        rental_stock_move_lines = sale_orders.order_line.filtered('is_rental').move_ids.move_line_ids

        if not rental_stock_move_lines:
            return res

        stock_move_lines = rental_stock_move_lines

        # Get the other customer invoices and refunds.
        ordered_invoice_ids = sale_orders.mapped('invoice_ids')\
            .filtered(lambda i: i.state not in ['draft', 'cancel'])\
            .sorted(lambda i: (i.invoice_date, i.id))

        # Get the position of self in other customer invoices and refunds.
        self_index = None
        i = 0
        for invoice in ordered_invoice_ids:
            if invoice.id == self.id:
                self_index = i
                break
            i += 1

        # Get the previous invoice if any.
        previous_invoices = ordered_invoice_ids[:self_index]
        last_invoice = previous_invoices[-1] if len(previous_invoices) else None

        # Get the incoming and outgoing sml between self.invoice_date and the previous invoice (if any).
        self_datetime = max(self.invoice_line_ids.mapped('write_date')) if self.invoice_line_ids else None
        last_invoice_datetime = max(last_invoice.invoice_line_ids.mapped('write_date')) if last_invoice else None

        def _filter_outgoing_sml(ml):
            # Rental moves send the products (& lots) to an internal location
            # independent of any warehouse (but still in the company to count for the assets).
            if ml.state == 'done' and ml.lot_id and ml.location_dest_id == ml.company_id.rental_loc_id :
                if last_invoice_datetime:
                    return last_invoice_datetime <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        # We only care about outgoing moves to display SN on invoices
        # we do not want to display more information atm, but could be nice to
        # say in invoicing report which SN have been returned and which not.
        outgoing_sml = stock_move_lines.filtered(_filter_outgoing_sml)

        # Prepare and return lot_values
        qties_per_lot = defaultdict(lambda: 0)
        for ml in outgoing_sml:
            qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)

        # VFE NOTE: The quantity may be wrong in some advanced cases:
        # When modifying pickedup or returned lots manually (e.g. not through the rental wizard),
        # You could remove already pickedup/returned lots, which would trigger the magical creation
        # of SML.
        # This means that if you return by error Lot A, then undo the return by removing the lot in the M2M,
        # 2 stocks moves would have been created.  Thus, on the invoice report, you would see 2 as qty for lot A...
        # Cf. magic move creation in sale_stock_renting/models/sale_rental.py

        lot_values = res
        for lot_id, qty in qties_per_lot.items():
            if float_is_zero(qty, precision_rounding=lot_id.product_id.uom_id.rounding):
                continue
            lot_values.append({
                'product_name': lot_id.product_id.display_name,
                'quantity': qty,
                'uom_name': lot_id.product_uom_id.name,
                'lot_name': lot_id.name,
                'lot_id': lot_id.id,
            })

        return lot_values
