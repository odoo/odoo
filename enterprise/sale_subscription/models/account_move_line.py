# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api
from odoo.tools.sql import column_exists, create_column


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _auto_init(self):
        # create column manually to skip initial computation
        if not column_exists(self.env.cr, "account_move_line", "subscription_mrr"):
            create_column(self.env.cr, "account_move_line", "subscription_mrr", "numeric")
        return super()._auto_init()

    subscription_id = fields.Many2one("sale.order", index=True)
    subscription_mrr = fields.Monetary(
        string="Monthly Recurring Revenue",
        compute="_compute_mrr",
        store=True,
        help="The MRR is computed by dividing the signed amount (in company currency) by the "
        "amount of time between the start and end dates converted in months.\nThis allows "
        "comparison of invoice lines created by subscriptions with different temporalities.\n"
        "The computation assumes that 1 month is comprised of exactly 30 days, regardless "
        " of the actual length of the month.",
    )

    # NOTE: deps on subscription_id are omitted by design, as it would trigger a recompute of
    # past data is a subscription's template where changed somehow
    # This computation should happen once and should basically be left as-is once done
    @api.depends("price_subtotal", "deferred_start_date", "deferred_end_date", "move_id.move_type")
    def _compute_mrr(self):
        """Compute the Subscription MRR for the line.

        The MRR is defined using generally accepted ratios used identically in the
        sale.order model to compute the MRR for a subscription; this method
        simply applies the same computation for a single invoice line for reporting
        purposes.
        """
        for line in self:
            if not (line.deferred_end_date and line.deferred_start_date):
                line.subscription_mrr = 0
                continue
            # we need to retro-compute the interval of the subscription as close as possible
            # hence the addition of 1 extra day to the end date - this mirrors the computation
            # of the next date in the subscription
            delta = relativedelta(
                dt1=line.deferred_end_date + relativedelta(days=1),
                dt2=line.deferred_start_date,
            )
            months = delta.months + delta.days / 30.0 + delta.years * 12.0
            line.subscription_mrr = line.price_subtotal / months if months else 0
            if line.move_id.move_type == "out_refund":
                line.subscription_mrr *= -1

    def copy_data(self, default=None):
        data_list = super().copy_data(default=default)
        for line, values in zip(self, data_list):
            if line.subscription_id:
                values['deferred_start_date'] = line.deferred_start_date
                values['deferred_end_date'] = line.deferred_end_date
        return data_list

    @api.depends('move_id.ref')
    def _compute_name(self):
        """
            This override is needed cause in the function _subscription_post_success_payment we do a write on the ref,
            the compute_name of the account_move_line is triggered again and override the description. So for line that
            have the boolean recurring_invoice we don't recompute the name.
        """
        move_line_to_recompute = self
        for line in move_line_to_recompute.filtered(lambda l: l.move_id.inalterable_hash is False):
            if line.sale_line_ids and all(sale_line.recurring_invoice for sale_line in line.sale_line_ids):
                move_line_to_recompute = move_line_to_recompute - line

        super(AccountMoveLine, move_line_to_recompute)._compute_name()

    def _sale_determine_order(self):
        mapping_from_invoice = super()._sale_determine_order()
        if mapping_from_invoice:
            renewed_subscriptions_ids = [
                so.id for so in mapping_from_invoice.values()
                if so.subscription_state == '5_renewed'
            ]
            child_orders = self.env['sale.order'].search([
                ('subscription_state', '=', '3_progress'),
                ('origin_order_id', 'in', renewed_subscriptions_ids),
            ], order='id ASC')
            # An AML in the mapping that is renewed but has no child orders indicates an invalid
            # state -> remove it from the mapping before returning.
            bad_aml_ids = []
            for aml_id, so in mapping_from_invoice.items():
                if so.subscription_state == '5_renewed':
                    origin_order_id = so.origin_order_id.id or so.id
                    min_child_order = next(
                        (child for child in child_orders if child.origin_order_id.id == origin_order_id),
                        None
                    )
                    if min_child_order:
                        mapping_from_invoice[aml_id] = min_child_order
                    else:
                        bad_aml_ids.append(aml_id)
            for aml_id in bad_aml_ids:
                del mapping_from_invoice[aml_id]
        return mapping_from_invoice

    def _get_max_invoiced_date(self):
        """ Util to determine the latest deferred_end_date of several account.move.line
        When full refunds are founds, their deferred_end_date are ignored because the corresponding period
        is not a period covered by the subscription contract. It may be reinvoiced later.
        Minimal change preserving the original behavior of not differentiating by product.
        """
        periods = {}

        for aml in self:
            if aml.move_id.state in ['draft', 'cancel'] or not aml.deferred_end_date:
                continue
            # Determine target UoM for quantity conversion
            # When the sale order line has been deleted, sale_line_ids is empty.
            # In that case, use the invoice line's own UoM as the target.
            if aml.sale_line_ids:
                target_uom = aml.sale_line_ids.product_uom
            elif aml.product_uom_id:
                target_uom = aml.product_uom_id
            else:
                continue
            sign = 1 if aml.move_id.move_type == 'out_invoice' else -1
            periods.setdefault(aml.deferred_end_date, 0.0)
            periods[aml.deferred_end_date] += sign * abs(aml.product_uom_id._compute_quantity(aml.quantity, target_uom, round=False))

        invoice_dates = [d for d, qty in periods.items() if qty > 0.0]

        return invoice_dates and max(invoice_dates)
