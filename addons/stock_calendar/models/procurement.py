from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID
from psycopg2 import OperationalError
from openerp.tools import float_compare, float_round
import pytz
import openerp

class procurement_order(osv.osv):
    _inherit = 'procurement.order'

    _columns = {
        'next_delivery_date': fields.datetime('Next Delivery Date',
                                              help="The date of the next delivery for this procurement group, when this group is on the purchase calendar of the orderpoint"),
        'next_purchase_date': fields.datetime('Next Purchase Date',
                                              help="The date the next purchase order should be sent to the vendor"),
        }

    def assign_group_date(self, cr, uid, ids, context=None):
        orderpoint_obj = self.pool.get("stock.warehouse.orderpoint")
        for procurement in self.browse(cr, uid, ids, context=context):
            ops = orderpoint_obj.search(cr, uid, [('location_id', '=', procurement.location_id.id),
                                                  ('product_id', '=', procurement.product_id.id)], context=context)
            if ops and ops[0]:
                orderpoint = orderpoint_obj.browse(cr, uid, ops[0], context=context)
                date_planned = datetime.strptime(procurement.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                purchase_date, delivery_date = self.pool['stock.orderpoint']._get_previous_dates(cr, uid, [orderpoint.id], date_planned, context=context)
                if purchase_date and delivery_date:
                    self.write(cr, uid, [procurement.id], {'next_delivery_date': delivery_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                         'next_purchase_date': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),}, context=context)

    def _get_purchase_order_date(self, schedule_date):
        if self.next_purchase_date:
            return datetime.strptime(self.next_purchase_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(procurement_order, self)._get_purchase_order_date(schedule_date)

    def _get_purchase_schedule_date(self):
        if self.next_delivery_date:
            return datetime.strptime(self.next_delivery_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(procurement_order, self)._get_purchase_schedule_date()

    def _prepare_purchase_order_line(self, cr, uid, ids, po, supplier, context=None):
        res = super(procurement_order, self)._prepare_purchase_order_line(cr, uid, ids, po, supplier, context=context)
        procurement = self.browse(cr, uid, ids, context=context)
        if procurement.next_delivery_date:
            res.update({'date_planned': procurement.next_delivery_date})
        return res

    def _procurement_from_orderpoint_get_order(self, cr, uid, context=None):
        return 'location_id, purchase_calendar_id, calendar_id'

    def _procurement_from_orderpoint_get_grouping_key(self, cr, uid, orderpoint_ids, context=None):
        orderpoint = self.pool['stock.warehouse.orderpoint'].browse(cr, uid, orderpoint_ids[0], context=context)
        return (orderpoint.location_id.id, orderpoint.purchase_calendar_id.id, orderpoint.calendar_id.id)

    def _procurement_from_orderpoint_get_groups(self, cr, uid, orderpoint_ids, context=None):
        orderpoint = self.pool['stock.warehouse.orderpoint'].browse(cr, uid, orderpoint_ids[0], context=context)
        res_groups = []
        date_groups = self._get_group(cr, uid, [orderpoint.id], context=context)
        for date, group in date_groups:
            if orderpoint.calendar_id and orderpoint.calendar_id.attendance_ids:
                date1, date2 = self._get_next_dates(cr, uid, [orderpoint.id], date, group, context=context)
                res_groups += [{'to_date': date2, 'procurement_values': {'group': group, 'date': date1, 'purchase_date': date}}]  # date1/date2 as deliveries and date as purchase confirmation date
            else:
                res_groups += [{'to_date': False, 'procurement_values': {'group': group, 'date': date, 'purchase_date': date}}]
        return res_groups

    def _procurement_from_orderpoint_post_process(self, cr, uid, orderpoint_ids, context=None):
        self.pool['stock.warehouse.orderpoint'].write(
            cr, uid, orderpoint_ids, {
                'last_execution_date': datetime.utcnow().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            }, context=context)
        return super(procurement_order, self)._procurement_from_orderpoint_post_process(cr, uid, orderpoint_ids, context=context)
