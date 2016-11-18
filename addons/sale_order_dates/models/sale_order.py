# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    """Add several date fields to Sale Orders, computed or user-entered"""
    _inherit = 'sale.order'

    commitment_date = fields.Datetime(compute='_compute_commitment_date', string='Commitment Date', store=True,
                                      help="Date by which the products are sure to be delivered. This is "
                                           "a date that you can promise to the customer, based on the "
                                           "Product Lead Times.")
    requested_date = fields.Datetime('Requested Date', readonly=True, states={'draft': [('readonly', False)],
                                     'sent': [('readonly', False)]}, copy=False,
                                     help="Date by which the customer has requested the items to be "
                                          "delivered.\n"
                                          "When this Order gets confirmed, the Delivery Order's "
                                          "expected date will be computed based on this date and the "
                                          "Company's Security Delay.\n"
                                          "Leave this field empty if you want the Delivery Order to be "
                                          "processed as soon as possible. In that case the expected "
                                          "date will be computed using the default method: based on "
                                          "the Product Lead Times and the Company's Security Delay.")
    effective_date = fields.Date(compute='_compute_picking_ids', string='Effective Date', store=True,
                                 help="Date on which the first Delivery Order was created.")

    @api.depends('date_order', 'order_line.customer_lead')
    def _compute_commitment_date(self):
        """Compute the commitment date"""
        for order in self:
            dates_list = []
            order_datetime = fields.Datetime.from_string(order.date_order)
            for line in order.order_line.filtered(lambda x: x.state != 'cancel'):
                dt = order_datetime + timedelta(days=line.customer_lead or 0.0)
                dates_list.append(dt)
            if dates_list:
                order.commitment_date = fields.Datetime.to_string(min(dates_list))

    def _compute_picking_ids(self):
        super(SaleOrder, self)._compute_picking_ids()
        for order in self:
            dates_list = []
            for pick in order.picking_ids:
                dates_list.append(fields.Datetime.from_string(pick.date))
            if dates_list:
                order.effective_date = fields.Datetime.to_string(min(dates_list))

    @api.onchange('requested_date')
    def onchange_requested_date(self):
        """Warn if the requested dates is sooner than the commitment date"""
        if (self.requested_date and self.commitment_date and self.requested_date < self.commitment_date):
            return {'warning': {
                'title': _('Requested date is too soon!'),
                'message': _("The date requested by the customer is "
                             "sooner than the commitment date. You may be "
                             "unable to honor the customer's request.")
                }
            }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_order_line_procurement(self, group_id):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
        for line in self.filtered("order_id.requested_date"):
            date_planned = fields.Datetime.from_string(line.order_id.requested_date) - timedelta(days=line.order_id.company_id.security_lead)
            vals.update({
                'date_planned': fields.Datetime.to_string(date_planned),
            })
        return vals
