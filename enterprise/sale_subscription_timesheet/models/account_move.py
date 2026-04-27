# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from datetime import timedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_range_dates(self, order):
        ''' Return the start and end dates for the subscription
        order's period to link the timesheets that just lays in
        between this period.
        :param order: order in which the dates are to be returned
        :return: a start date and end date for the subscription period
        '''
        start_date, end_date = super()._get_range_dates(order)
        if order.is_subscription and order.order_line.product_id.filtered(lambda p: p._is_delivered_timesheet()):
            return order.last_invoice_date, order.next_invoice_date + timedelta(days=-1)
        return start_date, end_date
