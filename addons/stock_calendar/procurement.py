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
                purchase_date, delivery_date = self._get_previous_dates(cr, uid, orderpoint, date_planned, context=context)
                if purchase_date and delivery_date:
                    self.write(cr, uid, [procurement.id], {'next_delivery_date': delivery_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                         'next_purchase_date': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),}, context=context)

    @api.v8
    def _get_purchase_order_date(self, schedule_date):
        if self.next_purchase_date:
            return datetime.strptime(self.next_purchase_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(procurement_order, self)._get_purchase_order_date(schedule_date)

    @api.v7
    def _get_purchase_order_date(self, cr, uid, procurement, company, schedule_date, context=None):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :param datetime schedule_date: desired Scheduled Date for the Purchase Order lines.
           :rtype: datetime
           :return: the desired Order Date for the PO
        """
        if procurement.next_purchase_date:
            return datetime.strptime(procurement.next_purchase_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(procurement_order, self)._get_purchase_order_date(cr, uid, procurement, company, schedule_date, context=context)

    @api.v8
    def _get_purchase_schedule_date(self):
        if self.next_delivery_date:
            return datetime.strptime(self.next_delivery_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(procurement_order, self)._get_purchase_schedule_date()

    @api.v7
    def _get_purchase_schedule_date(self, cr, uid, procurement, context=None):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement.

           :param browse_record procurement: the procurement for which a PO will be created.
           :rtype: datetime
           :return: the desired Schedule Date for the PO lines
        """
        if procurement.next_delivery_date:
            return datetime.strptime(procurement.next_delivery_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(procurement_order, self)._get_purchase_schedule_date(cr, uid, procurement, context=context)

    def _prepare_purchase_order_line(self, cr, uid, ids, po, supplier, context=None):
        res = super(procurement_order, self)._prepare_purchase_order_line(cr, uid, ids, po, supplier, context=context)
        procurement = self.browse(cr, uid, ids, context=context)
        if procurement.next_delivery_date:
            res.update({'date_planned': procurement.next_delivery_date})
        return res

    def _get_previous_dates(self, cr, uid, orderpoint, start_date = False, context=None):
        """
        Date should be given in utc
        """
        calendar_obj = self.pool.get('resource.calendar')
        att_obj = self.pool.get('resource.calendar.attendance')
        context = context or {}
        context['no_round_hours'] = True
        # First check if the orderpoint has a Calendar as it should be delivered at this calendar date
        purchase_date = False
        delivery_date = start_date
        if orderpoint.calendar_id and orderpoint.calendar_id.attendance_ids:
            res = calendar_obj._schedule_days(cr, uid, orderpoint.calendar_id.id, -1, start_date, compute_leaves=True, context=context)
            if res and res[0][0] < start_date:
                group_to_find = res[0][2] and att_obj.browse(cr, uid, res[0][2], context=context).group_id.id or False
                delivery_date = res[0][0]
                found_date = delivery_date
                if orderpoint.purchase_calendar_id and orderpoint.purchase_calendar_id.attendance_ids:
                    while not purchase_date:
                        found_date = found_date + relativedelta(days=-1) # won't allow to deliver within the day
                        res = calendar_obj._schedule_days(cr, uid, orderpoint.purchase_calendar_id.id, -1, found_date, compute_leaves=True, context=context)
                        for re in res:
                            group = re[2] and att_obj.browse(cr, uid, re[2], context=context).group_id.id or False
                            found_date = re[0]
                            if not purchase_date and (group_to_find and group_to_find == group or (not group_to_find)):
                                purchase_date = re[0]
        else:
            delivery_date = start_date or datetime.utcnow()
        return purchase_date, delivery_date

    def _get_next_dates(self, cr, uid, orderpoint, new_date=False, group=False, context=None):
        calendar_obj = self.pool.get('resource.calendar')
        att_obj = self.pool.get('resource.calendar.attendance')
        context = context or {}
        context['no_round_hours'] = True
        if not new_date:
            new_date = datetime.utcnow()
        now_date = datetime.utcnow()

        # Search first calendar day (without group)
        res = calendar_obj._schedule_days(cr, uid, orderpoint.calendar_id.id, 1, new_date, compute_leaves=True, context=context)
        att_group = res and res[0][2] and att_obj.browse(cr, uid, res[0][2], context=context).group_id.id or False
        #If hours are smaller than the current date, search a day further
        if res and res[0][0] < now_date:
            new_date = res[0][1] + relativedelta(days=1)
            res = calendar_obj._schedule_days(cr, uid, orderpoint.calendar_id.id, 1, new_date, compute_leaves=True, context=context)
            for re in res:
                att_group = False
                if re[2]:
                    att_group = att_obj.browse(cr, uid, re[2], context=context).group_id.id
                    if att_group == group:
                        break

        # If you can find an entry and you have a group to match, but it does not, search further until you find one that corresponds
        number = 0
        while res and group and att_group != group and number < 100:
            number += 1
            new_date = res[0][1] + relativedelta(days=1)
            res = calendar_obj._schedule_days(cr, uid, orderpoint.calendar_id.id, 1, new_date, compute_leaves=True, context=context)
            att_group = False
            for re in res:
                if re[2]:
                    att_group = att_obj.browse(cr, uid, re[2], context=context).group_id.id
                    if att_group == group:
                        break
        #number as safety pall for endless loops
        if number >= 100:
            res = False

        # If you found a solution(first date), you need the second date until the next delivery because you need to deliver
        # everything needed until the second date on the first date
        if res:
            date1 = res[0][1]
            new_date = res[0][1] + relativedelta(days=1)
            res = calendar_obj._schedule_days(cr, uid, orderpoint.calendar_id.id, 1, new_date, compute_leaves=True, context=context)
            if res:
                return (date1, res[0][1])
        return (False, False)

    def _get_group(self, cr, uid, orderpoint, context=None):
        """
            Will return the groups and the end dates of the intervals of the purchase calendar
            that need to be executed now.
            If a purchase calendar is defined, it should give the
            :return [(date, group)]
        """
        #Check if orderpoint has last execution date and calculate if we need to calculate again already
        calendar_obj = self.pool.get("resource.calendar")
        att_obj = self.pool.get("resource.calendar.attendance")
        group = False
        context = context or {}
        context = dict(context, no_round_hours=True)
        date = False
        now_date = datetime.utcnow()
        res_intervals = []
        if orderpoint.purchase_calendar_id and orderpoint.purchase_calendar_id.attendance_ids:
            if orderpoint.last_execution_date:
                new_date = datetime.strptime(orderpoint.last_execution_date, DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                new_date = datetime.utcnow()
            # TDE note: I bet accessing interval[2] will crash, no ? this code seems very louche
            intervals = calendar_obj._schedule_days(cr, uid, orderpoint.purchase_calendar_id.id, 1, new_date, compute_leaves=True, context=context)
            for interval in intervals:
                # If last execution date, interval should start after it in order not to execute the same orderpoint twice
                # TODO: Make the interval a little bigger
                if (orderpoint.last_execution_date and (interval[0] > new_date and interval[0] < now_date)) or (not orderpoint.last_execution_date and interval[0] < now_date and interval[1] > now_date):
                    group = att_obj.browse(cr, uid, interval[2], context=context).group_id.id
                    date = interval[1]
                    res_intervals += [(date, group), ]
        else:
            return [(now_date, None)]
        return res_intervals

    def _procurement_from_orderpoint_get_order(self, cr, uid, context=None):
        return 'location_id, purchase_calendar_id, calendar_id'

    def _procurement_from_orderpoint_get_grouping_key(self, cr, uid, orderpoint_ids, context=None):
        orderpoint = self.pool['stock.warehouse.orderpoint'].browse(cr, uid, orderpoint_ids[0], context=context)
        return (orderpoint.location_id.id, orderpoint.purchase_calendar_id.id, orderpoint.calendar_id.id)

    def _procurement_from_orderpoint_get_groups(self, cr, uid, orderpoint_ids, context=None):
        orderpoint = self.pool['stock.warehouse.orderpoint'].browse(cr, uid, orderpoint_ids[0], context=context)
        res_groups = []
        date_groups = self._get_group(cr, uid, orderpoint, context=context)
        for date, group in date_groups:
            if orderpoint.calendar_id and orderpoint.calendar_id.attendance_ids:
                date1, date2 = self._get_next_dates(cr, uid, orderpoint, date, group, context=context)
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
