# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class sale_order_dates(osv.osv):
    """Add several date fields to Sale Orders, computed or user-entered"""
    _inherit = 'sale.order'

    def _get_effective_date(self, cr, uid, ids, name, arg, context=None):
        """Read the shipping date from the related packings"""
        # TODO: would be better if it returned the date the picking was processed?
        res = {}
        dates_list = []
        for order in self.browse(cr, uid, ids, context=context):
            dates_list = []
            for pick in order.picking_ids:
                dates_list.append(pick.date)
            if dates_list:
                res[order.id] = min(dates_list)
            else:
                res[order.id] = False
        return res

    def _get_commitment_date(self, cr, uid, ids, name, arg, context=None):
        """Compute the commitment date"""
        res = {}
        dates_list = []
        for order in self.browse(cr, uid, ids, context=context):
            dates_list = []
            order_datetime = datetime.strptime(order.date_order, DEFAULT_SERVER_DATETIME_FORMAT)
            for line in order.order_line:
                if line.state == 'cancel':
                    continue
                dt = order_datetime + timedelta(days=line.customer_lead or 0.0)
                dt_s = dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                dates_list.append(dt_s)
            if dates_list:
                res[order.id] = min(dates_list)
        return res

    def onchange_requested_date(self, cr, uid, ids, requested_date,
                                commitment_date, context=None):
        """Warn if the requested dates is sooner than the commitment date"""
        if (requested_date and commitment_date and requested_date < commitment_date):
            return {'warning': {
                'title': _('Requested date is too soon!'),
                'message': _("The date requested by the customer is "
                             "sooner than the commitment date. You may be "
                             "unable to honor the customer's request.")
                }
            }
        return {}

    _columns = {
        'commitment_date': fields.function(_get_commitment_date, store=True,
            type='datetime', string='Commitment Date',
            help="Date by which the products are sure to be delivered. This is "
                 "a date that you can promise to the customer, based on the "
                 "Product Lead Times."),
        'requested_date': fields.datetime('Requested Date',
            readonly=True, states={'draft': [('readonly', False)],
                                   'sent': [('readonly', False)]}, copy=False,
            help="Date by which the customer has requested the items to be "
                 "delivered.\n"
                 "When this Order gets confirmed, the Delivery Order's "
                 "expected date will be computed based on this date and the "
                 "Company's Security Delay.\n"
                 "Leave this field empty if you want the Delivery Order to be "
                 "processed as soon as possible. In that case the expected "
                 "date will be computed using the default method: based on "
                 "the Product Lead Times and the Company's Security Delay."),
        'effective_date': fields.function(_get_effective_date, type='date',
            store=True, string='Effective Date',
            help="Date on which the first Delivery Order was created."),
    }


class SaleOrderLine(osv.osv):
    _inherit = 'sale.order.line'

    def _prepare_order_line_procurement(self, cr, uid, ids, group_id=False, context=None):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(cr, uid, ids, group_id=group_id, context=context)
        line = self.browse(cr, uid, ids, context=context)
        if line.order_id.requested_date:
            date_planned = datetime.strptime(line.order_id.requested_date, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(days=line.order_id.company_id.security_lead)
            vals.update({
                'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })
        return vals
