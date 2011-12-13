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
from tools.translate import _
from tools import DEFAULT_SERVER_DATE_FORMAT

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
                dt = (datetime.strptime(order.date_order,
                                        DEFAULT_SERVER_DATE_FORMAT)
                     + relativedelta(days=line.delay or 0.0) )
                dt_s = dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                dates_list.append(dt_s)
            if dates_list:
                res[order.id] = min(dates_list)
        return res

    def onchange_requested_date(self, cr, uid, ids, requested_date,
                                commitment_date, context=None):
        """Warn if the requested dates is sooner than the commitment date"""
        if requested_date < commitment_date:
            lang = self.pool.get("res.users").browse(cr, uid, uid,
                                                 context=context).context_lang
            if lang:
                lang_ids = self.pool.get('res.lang').search(cr, uid,
                                                     [('code', '=', lang)])
                date_format = self.pool.get("res.lang").browse(cr, uid,
                                    lang_ids, context=context)[0].date_format
                # Parse the dates...
                req_date_formated = datetime.strptime(requested_date,
                                                  DEFAULT_SERVER_DATE_FORMAT)
                com_date_formated = datetime.strptime(commitment_date,
                                                  DEFAULT_SERVER_DATE_FORMAT)
                # ... and reformat them according to the user's language
                req_date_formated = req_date_formated.strftime(date_format)
                com_date_formated = com_date_formated.strftime(date_format)
            else:
                req_date_formated = requested_date
                com_date_formated = commitment_date
            print lang, req_date_formated, com_date_formated
            return {'warning': {
                'title': _('Requested date is too soon!'),
                'message': _("The date requested by the customer (%s) is "
                             "sooner than the commitment date (%s). You may be "
                             "unable to honor the customer's request." % 
                                 (req_date_formated, com_date_formated))
                }
            }
        else:
            return {}

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