# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_in_b2c_invoice_number = fields.Char(
        string='B2C Invoice Number',
        readonly=True,
        copy=False,
        index='btree_not_null',
        help="GST invoice number given to this order when it is paid without being invoiced, from the B2C sequence of its Point of Sale.",
    )
    l10n_in_b2c_invoice_prefix = fields.Char(
        string='B2C Invoice Prefix',
        readonly=True,
        copy=False,
        help='Prefix of the B2C invoice number, the series the number belongs to in the GSTR-1 document summary.',
    )

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self._l10n_in_assign_b2c_invoice_number()
        return res

    def _l10n_in_assign_b2c_invoice_number(self):
        self.ensure_one()
        if self.l10n_in_b2c_invoice_number or self.country_code != 'IN':
            return
        # A refund keeps the B2B nature of the order it refunds, and an invoiced order has its invoice number.
        if self.to_invoice or self.refunded_order_id.to_invoice:
            return
        sequence = (
            self.config_id.l10n_in_b2c_refund_sequence_id
            if self.is_refund_or_negative()
            else self.config_id.l10n_in_b2c_sequence_id
        )
        # Number in the company's local year of the order, even if it is synced later.
        order_date = fields.Datetime.context_timestamp(self.with_context(tz=self.company_id.tz), self.date_order).date()
        sequence = sequence.sudo()
        number = sequence.next_by_id(sequence_date=order_date)
        # The prefix as interpolated for this number, its prefix and date range can change afterwards.
        date_range = sequence.date_range_ids.filtered(lambda dr: dr.date_from <= order_date <= dr.date_to)[:1]
        prefix = sequence._get_prefix_suffix(date=order_date, date_range=date_range.date_from)[0]
        self.write({
            'l10n_in_b2c_invoice_number': number,
            'l10n_in_b2c_invoice_prefix': prefix,
        })

    def _l10n_in_is_reversed_by_credit_note(self):
        return (
            len(self) == 1
            and self.country_code == 'IN'
            and bool(self.l10n_in_b2c_invoice_number)
            and not self.is_refund_or_negative()
        )

    def _grouping_function(self, line):
        res = super()._grouping_function(line)  # Returns mappingproxy (immutable)
        if self.config_id.company_id.l10n_in_gst_registration_type:
            res = dict(res)  # Convert to mutable dict
            res['l10n_in_hsn_code'] = line.get('l10n_in_hsn_code', '')
            res['product_uom_id'] = line.get('product_uom_id', '')
        return res

    def _prepare_account_move_line_data(self, aggregate=True):
        lines = super()._prepare_account_move_line_data(aggregate)
        if aggregate:
            return lines

        for line in lines:
            move = line.get('account.move.line')
            meta = line.get('metadata')

            if self.config_id.company_id.l10n_in_gst_registration_type and meta:
                pos_line = meta.get('line') if meta else None
                if not pos_line:
                    continue
                move["l10n_in_hsn_code"] = pos_line.l10n_in_hsn_code
                move["product_uom_id"] = pos_line.product_uom_id.id

        return lines

    def _prepare_move_line_vals_from_base_line(self, base_line):
        values = super()._prepare_move_line_vals_from_base_line(base_line)
        if self.config_id.company_id.l10n_in_gst_registration_type:
            values["l10n_in_hsn_code"] = base_line.get("l10n_in_hsn_code", "")
            values["product_uom_id"] = base_line.get("product_uom_id", "").id
        return values
