# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class sale_order_dates(osv.osv):
    """Add several date fields to Sale Orders, computed or user-entered"""
    _inherit = 'sale.order'

    def _get_date_planned(self, cr, uid, order, line, start_date, context=None):
        """Compute the expected date from the requested date, not the order date"""
        if order and order.requested_date:
            date_planned = datetime.strptime(order.requested_date, DEFAULT_SERVER_DATETIME_FORMAT)
            date_planned -= timedelta(days=order.company_id.security_lead)
            return date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return super(sale_order_dates, self)._get_date_planned(
                cr, uid, order, line, start_date, context=context)

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
                dt = order_datetime + timedelta(days=line.delay or 0.0)
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
            readonly=True, states={'draft': [('readonly', False)]}, copy=False,
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
