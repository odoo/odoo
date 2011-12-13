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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import fields, osv

class sale_order_dates(osv.osv):
    """Add several date fields to Sale Orders, computed or user-entered"""
    _inherit = 'sale.order'

    def _get_effective_date(self, cr, uid, ids, name, arg, context=None):
        """Read the shipping date from the related packings"""
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
    
    def _prepare_order_picking(self, cr, uid, order, *args):
        """Take the requested date into account when creating the picking"""
        picking_data = super(sale_order_dates, self)._prepare_order_picking(cr,
                                                             uid, order, *args)
        picking_data['date'] = order.requested_date
        return picking_data

    def _get_commitment_date(self, cr, uid, ids, name, arg, context=None):
        """Compute the commitment date"""
        res = {}
        dates_list = []
        for order in self.browse(cr, uid, ids, context=context):
            dates_list = []
            for line in order.order_line:
                dt = (datetime.strptime(order.date_order, '%Y-%m-%d')
                     + relativedelta(days=line.delay or 0.0) )
                dt_s = dt.strftime('%Y-%m-%d')
                dates_list.append(dt_s)
            if dates_list:
                res[order.id] = min(dates_list)
        return res

    _columns = {
        'commitment_date': fields.function(_get_commitment_date, store=True,
            type='date', string='Commitment Date',
            help="Date by which the products must be delivered."),
        'requested_date': fields.date('Requested Date',
            help="Date by which the customer has requested the products to be delivered."),
        'effective_date': fields.function(_get_effective_date, type='date',
            store=True, string='Effective Date',
            help="Date on which shipping is created."),
    }

sale_order_dates()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: