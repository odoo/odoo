# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    """Add several date fields to Sales Orders, computed or user-entered"""
    _inherit = 'sale.order'

    expected_date = fields.Datetime(compute='_compute_expected_date',
        string='Expected Date', store=False, oldname='commitment_date',
        help="Delivery date you can promise to the customer, computed from "
             "product lead times and from the shipping policy of the order.")
    commitment_date = fields.Datetime('Commitment Date',
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        copy=False, oldname='requested_date', readonly=True,
        help="This is the delivery date promised to the customer. If set, the delivery order "
             "will be scheduled based on this date rather than product lead times.")
    effective_date = fields.Date(compute='_compute_effective_date',
        string='Effective Date', store=True,
        help="Completion date of the first delivery order.")

    @api.depends('order_line.customer_lead', 'confirmation_date', 'picking_policy', 'order_line.state')
    def _compute_expected_date(self):
        """Compute the expected date"""
        for order in self:
            dates_list = []
            confirm_date = fields.Datetime.from_string(order.confirmation_date if order.state == 'sale' else fields.Datetime.now())
            for line in order.order_line.filtered(lambda x: x.state != 'cancel'):
                dt = confirm_date + timedelta(days=line.customer_lead or 0.0)
                dates_list.append(dt)
            if dates_list:
                expected_date = min(dates_list) if order.picking_policy == 'direct' else max(dates_list)
                order.expected_date = fields.Datetime.to_string(expected_date)

    @api.depends('picking_ids.date_done')
    def _compute_effective_date(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
            dates_list = pickings.mapped('date_done')
            order.effective_date = dates_list and min(dates_list)

    @api.onchange('commitment_date')
    def onchange_commitment_date(self):
        """Warn if the commitment dates is sooner than the expected date"""
        if (self.commitment_date and self.expected_date and self.commitment_date < self.expected_date):
            return {'warning': {
                'title': _('Requested date is too soon.'),
                'message': _("The date requested by the customer is "
                             "sooner than the commitment date. You may be "
                             "unable to honor the customer's request.")
                }
            }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_procurement_values(self, group_id):
        vals = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        for line in self.filtered("order_id.commitment_date"):
            date_planned = fields.Datetime.from_string(line.order_id.commitment_date) - timedelta(days=line.order_id.company_id.security_lead)
            vals.update({
                'date_planned': fields.Datetime.to_string(date_planned),
            })
        return vals
