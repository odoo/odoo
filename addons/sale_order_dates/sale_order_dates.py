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
from dateutil.relativedelta import relativedelta

from osv import fields, osv
from tools.translate import _
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class sale_order_dates(osv.osv):
    """Add several date fields to Sale Orders, computed or user-entered"""
    _inherit = 'sale.order'

    def copy(self, cr, uid, id, default=None, context=None):
        """Don't copy the requested date along with the Sale Order"""
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['requested_date'] = False
        return super(sale_order_dates, self).copy(cr, uid, id, default=default,
                                            context=context)
    
    def _order_line_move_date(self, cr, uid, line):
        """Compute the expected date from the requested date, not the order date"""
        order=line.order_id
        if order and order.requested_date:
            date_planned = datetime.strptime(order.requested_date,
                                             DEFAULT_SERVER_DATE_FORMAT)
            date_planned -= timedelta(days=order.company_id.security_lead)
            return date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        else:
            return super(sale_order_dates, self)._order_line_move_date(cr, uid, line)
        
    def _get_effective_date(self, cr, uid, ids, name, arg, context=None):
        """Read the shipping date from the related packings"""
        # XXX would be better if it returned the date the picking was processed
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
        if (requested_date and commitment_date
                           and requested_date < commitment_date):
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
            help="Date by which the products is sure to be delivered. This is "
                 "a date that you can promise to the customer, based on the "
                 "Product Lead Times."),
        'requested_date': fields.date('Requested Date',
            readonly=True, states={'draft': [('readonly', False)]},
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

sale_order_dates()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: