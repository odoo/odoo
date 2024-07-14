# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, timedelta
import pytz

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.tools import float_utils, DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.resource.models.utils import Intervals

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    start_datetime = fields.Datetime(required=False)
    end_datetime = fields.Datetime(required=False)
    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Item', domain=[('product_id.type', '=', 'service'), ('state', 'not in', ['draft', 'sent'])],
        index=True, ondelete='cascade', group_expand='_group_expand_sale_line_id',
        help="Sales order item for which this shift will be performed. When sales orders are automatically planned,"
             " the remaining hours of the sales order item, as well as the role defined on the service, are taken into account.")
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', related='sale_line_id.order_id', store=True)
    partner_id = fields.Many2one('res.partner', related='sale_order_id.partner_id')
    role_product_ids = fields.One2many('product.template', related='role_id.product_ids')
    sale_line_plannable = fields.Boolean(related='sale_line_id.product_id.planning_enabled')
    allocated_hours = fields.Float(compute_sudo=True)

    _sql_constraints = [
        ('check_datetimes_set_or_plannable_slot',
         'CHECK((start_datetime IS NOT NULL AND end_datetime IS NOT NULL) OR sale_line_id IS NOT NULL)',
         'Only slots linked to a sale order with a plannable service can be unscheduled.')
    ]

    @api.depends('sale_line_id')
    def _compute_role_id(self):
        slot_with_sol = self.filtered('sale_line_plannable')
        for slot in slot_with_sol:
            if not slot.role_id:
                slot.role_id = slot.sale_line_id.product_id.planning_role_id
        super(PlanningSlot, self - slot_with_sol)._compute_role_id()

    @api.depends('start_datetime', 'sale_line_id.planning_hours_to_plan', 'sale_line_id.planning_hours_planned')
    def _compute_allocated_hours(self):
        if self.env.context.get('sale_planning_prevent_recompute'):
            return
        planned_slots = self.filtered('start_datetime')
        for slot in self - planned_slots:
            if slot.sale_line_id:
                slot.allocated_hours = max(
                    slot.sale_line_id.planning_hours_to_plan - slot.sale_line_id.planning_hours_planned,
                    0.0
                )
        super(PlanningSlot, planned_slots)._compute_allocated_hours()
        SaleOrderLine = self.env['sale.order.line']
        self.env.add_to_compute(SaleOrderLine._fields['planning_hours_planned'], self.sale_line_id)

    @api.depends('start_datetime')
    def _compute_allocated_percentage(self):
        planned_slots = self.filtered('start_datetime')
        super(PlanningSlot, planned_slots)._compute_allocated_percentage()

    @api.depends('start_datetime')
    def _compute_past_shift(self):
        planned_slots = self.filtered('start_datetime')
        (self - planned_slots).is_past = False
        super(PlanningSlot, planned_slots)._compute_past_shift()

    @api.depends('start_datetime')
    def _compute_unassign_deadline(self):
        planned_slots = self.filtered('start_datetime')
        (self - planned_slots).unassign_deadline = False
        super(PlanningSlot, planned_slots)._compute_unassign_deadline()

    @api.depends('start_datetime')
    def _compute_is_unassign_deadline_passed(self):
        planned_slots = self.filtered('start_datetime')
        (self - planned_slots).is_unassign_deadline_passed = False
        super(PlanningSlot, planned_slots)._compute_is_unassign_deadline_passed()

    @api.depends('start_datetime')
    def _compute_working_days_count(self):
        planned_slots = self.filtered('start_datetime')
        (self - planned_slots).working_days_count = 0
        super(PlanningSlot, planned_slots)._compute_working_days_count()

    @api.depends('start_datetime')
    def _compute_template_autocomplete_ids(self):
        planned_slots = self.filtered('start_datetime')
        (self - planned_slots).template_autocomplete_ids = self.template_id
        super(PlanningSlot, planned_slots)._compute_template_autocomplete_ids()

    def _group_expand_sale_line_id(self, sale_lines, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, (list, tuple)) and len(dom) == 3]
        sale_line_ids = self.env.context.get('filter_sale_line_ids', False)
        if sale_line_ids:
            # search method is used rather than browse since the order needs to be handled
            return self.env['sale.order.line'].search([('id', 'in', sale_line_ids)], order=order)
        elif self._context.get('planning_expand_sale_line_id') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('sale_line_id', '=') in dom_tuples or ('sale_line_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'sale_line_id')
                return self.env['sale.order.line'].search(filter_domain, order=order)
            filters = self._expand_domain_dates(domain)
            sale_lines = self.env['planning.slot'].search(filters).mapped('sale_line_id')
            return sale_lines.search([('id', 'in', sale_lines.ids)], order=order)
        return sale_lines

    # -----------------------------------------------------------------
    # ORM Override
    # -----------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('sale_line_id'):
            sale_line_id = self.env['sale.order.line'].browse(res.get('sale_line_id'))
            if sale_line_id.product_id.planning_enabled and res.get('start_datetime') and res.get('end_datetime'):
                remaining_hours_to_plan = sale_line_id.planning_hours_to_plan - sale_line_id.planning_hours_planned
                if float_utils.float_compare(remaining_hours_to_plan, 0, precision_digits=2) < 1:
                    return res
                allocated_hours = (res['end_datetime'] - res['start_datetime']).total_seconds() / 3600.0
                if float_utils.float_compare(remaining_hours_to_plan, allocated_hours, precision_digits=2) < 1:
                    res['end_datetime'] = res['start_datetime'] + timedelta(hours=remaining_hours_to_plan)
        return res

    def _display_name_fields(self):
        """ List of fields that can be displayed in the display_name """
        return ['partner_id'] + super()._display_name_fields() + ['sale_line_id']

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res.sale_line_id:
            res.sale_line_id.sudo()._compute_planning_hours_planned()  # ensure it is computed before doing postprocess
            res.sale_line_id.sudo()._post_process_planning_sale_line(ids_to_exclude=res.ids)
        return res

    def write(self, vals):
        self.assign_slot(vals)
        return True

    def assign_slot(self, vals):
        sale_order_slots_to_plan = []
        PlanningShift = self.env['planning.slot']
        slots_to_write = PlanningShift
        slots_written = PlanningShift
        if vals.get('start_datetime'):
            # if the previous start_datetime was False, it means the slot has been selected from the
            # unscheduled slots. In this case, slots must be generated automatically to fill the gantt period
            # with the hours remaining to plan of the linked sale order as a limit of hours to allocate.
            slot_vals_list_per_employee = defaultdict(list)
            for slot in self:
                if slot.sale_line_plannable and not slot.start_datetime:
                    # This method will generate the planning slots for the given employee and following the numbers of hours still to plan
                    # for the given slot's sale order line.
                    new_vals, tmp_sale_order_slots_to_plan, resource = slot._get_sale_order_slots_to_plan(vals, slot_vals_list_per_employee)
                    if new_vals:
                        # Call the write method of the parent
                        super(PlanningSlot, slot).write(new_vals[0])
                        slots_written += slot
                        sale_order_slots_to_plan += tmp_sale_order_slots_to_plan
                        if resource:
                            slot_vals_list_per_employee[resource] += new_vals + tmp_sale_order_slots_to_plan
                else:
                    slots_to_write |= slot
        else:
            slots_to_write |= self

        super(PlanningSlot, slots_to_write).write(vals)
        slots_written += slots_to_write

        if sale_order_slots_to_plan:
            slots_written += self.create(sale_order_slots_to_plan)

        slots_to_unlink = PlanningShift
        for slot in self:
            if slot.sale_line_id and not slot.start_datetime and float_utils.float_compare(slot.allocated_hours, 0.0, precision_digits=2) < 1:
                slots_to_unlink |= slot
        if (self - slots_to_unlink).sale_line_id:
            (self - slots_to_unlink).sale_line_id.sudo()._post_process_planning_sale_line(ids_to_exclude=self.ids)
        slots_to_unlink.unlink()
        return slots_written - slots_to_unlink

    # -----------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------

    def action_view_sale_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    # -----------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------

    def _get_domain_template_slots(self):
        domain = super()._get_domain_template_slots()
        if self.sale_line_plannable:
            domain = expression.AND([domain, ['|', ('role_id', '=', self.sale_line_id.product_id.planning_role_id.id), ('role_id', '=', False)]])
        return domain

    def _get_sale_order_slots_to_plan(self, vals, slot_vals_list_per_resource):
        """
            Returns the vals which will be used to update self, a vals_list of the slots
            to create for the same related sale_order_line and the resource.

            :param vals: the vals passed to the write orm method.
            :param slot_vals_list_per_resource: a dict of vals list of slots to be created, sorted per resource
                This dict is used to be aware of the slots which will be created and are not in the database yet.
        """
        # Gets work interval in order to know if the employee can work or not
        # Gets its slots which are partially allocated (allocated_percentage < 100) in order to avoid planning slots in conflict.
        self.ensure_one()
        to_allocate = self.sale_line_id.planning_hours_to_plan - self.sale_line_id.planning_hours_planned
        if to_allocate < 0.0:
            return [], [], None
        work_intervals, unforecastable_intervals, resource, partial_interval_slots = self.sudo().with_context(
            default_end_datetime=self.env.context.get('default_end_datetime')
        )._get_resource_work_info(vals, slot_vals_list_per_resource)
        following_slots_vals_list = []
        if work_intervals:
            following_slots_vals_list = self._get_slots_values(
                vals, work_intervals, partial_interval_slots, unforecastable_intervals, to_allocate=to_allocate, resource=resource
            )
            if following_slots_vals_list:
                # In order to have slots on multiple days, the slots filling the resource's work intervals must be
                # merged. The consequence is that it will be forecasted slots (regarding `allocation_type`) rather than short planning slots
                following_slots_vals_list = self._merge_slots_values(following_slots_vals_list, unforecastable_intervals)
                return following_slots_vals_list[:1], following_slots_vals_list[1:], resource
        return [], [], resource

    def _get_slots_values(self, vals, work_intervals, partial_interval_slots, unforecastable_intervals, to_allocate, resource):
        """
            This method returns the generated slots values related to self.sale_line_id for the given resource.

            Params :
                - `vals` : the vals sent in the write/reschedule call;
                - `work_intervals`: Intervals during which resource works/is available
                - `partial_interval_slots`: Intervals during which the resource have slots partially planned (`allocated_percentage` < 100)
                - `unforecastable_intervals`: Intervals during which the resource cannot have a slot with `allocation_type` == 'forecast'
                                          (see _merge_slots_values for further explanation)
                - `to_allocate`: The number of hours there is still to allocate for this self.sale_line_id
                - `resource`: The recordset of the resource for whom the information are given and who will be assigned to the slots
                                 If None, the information is the one of the company.

            Algorithm :
                - General principle :
                    - For each work interval, a planning slot is assigned to the employee, until there are no more hours to allocate
                - Details :
                    - If the interval is in conflict with a partial_interval_slots, the algorithm must find each time the sum of allocated_percentage increases/decreases:
                        - The algorithm retrieve this information by building a dict where the keys are the datetime where the allocated_percentage changes :
                            - The algorithm adds start and end of the interval in the dict with 0 as value to increase/decrease
                            - For each slot conflicting with the work_interval:
                                - allocated_percentage is added with start_datetime as a key,
                                - allocated_percentage is substracted with end_datetime as a key
                            - For each datetime where the allocated_percentage changes:
                                - if there are no allocated percentage change (sum = 0) in the next allocated percentage change:
                                    - It will create a merged slot and not divide it in small parts
                                - the allocable percentage (default=100) is decreased by the value in the dict for the previous datetime (which will be the start datetime of the slot)
                                - if there are still time to allocate
                                    - Otherwise, it continues with the next datetime with allocated percentage change.
                                - if the datetimes are contained in the interval
                                    - Otherwise, it continues with the next datetime with allocated percentage change.
                                - The slot is build with the previous datetime with allocated percentage change and the actual datetime.
                    - Otherwise,
                        - Take the start of the interval as the start_datetime of the slot
                        - Take the min value between the end of the interval and the sum of the interval start and to_allocate hours.
                - Generate an unplanned slot if there are still hours to allocate.

            Returns :
                - A vals_list with slots to create :
                    NB : The first item of the list will be used to update the current slot.
        """
        self.ensure_one()
        following_slots_vals_list = []
        for interval in work_intervals:
            if float_utils.float_compare(to_allocate, 0.0, precision_digits=2) < 1:
                break
            start_interval = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
            end_interval = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
            if partial_interval_slots[interval]:
                # here we'll create slots with partially allocated hours - which is not trivial btw - read above the full explanation
                # 1. Create a dict with a datetime as `key`, which represent the total *increment* of allocated time, starting from time: `key`
                #    So for each slot, the increment is increased with allocated percentage at start datetime and decrease it at end datetime
                # 2. Create a list with all the start and end dates (allocated_dict keys), which will be sorted in order to have all the intervals.
                # 3. Allocable percentage are tracked by decreasing previous allocable percentage with the *increment* of allocated time.
                allocated_dict = defaultdict(float)
                allocated_dict.update({
                    start_interval: 0,
                    end_interval: 0,
                })
                for slot in partial_interval_slots[interval]:
                    allocated_dict[slot['start_datetime']] += float_utils.float_round(slot['allocated_percentage'], precision_digits=1)
                    allocated_dict[slot['end_datetime']] += float_utils.float_round(-slot['allocated_percentage'], precision_digits=1)
                datetime_list = list(allocated_dict.keys())
                datetime_list.sort()
                allocable = 100.0
                for i in range(1, len(datetime_list)):
                    start_dt = datetime_list[i - 1]
                    end_dt = datetime_list[i]
                    if i != len(datetime_list) - 1 and float_utils.float_is_zero(allocated_dict[datetime_list[i]], precision_digits=2):
                        # there is no increment so we will build a single slot with the same allocated_percentage
                        datetime_list[i] = datetime_list[i - 1]
                        continue
                    allocable -= float_utils.float_round(allocated_dict[datetime_list[i - 1]], precision_digits=1)
                    if float_utils.float_compare(allocable, 0.0, precision_digits=2) < 1:
                        unforecastable_intervals |= Intervals([(
                            pytz.utc.localize(start_dt),
                            pytz.utc.localize(end_dt),
                            self.env['resource.calendar.leaves'])])
                        continue
                    if end_dt <= start_interval or start_dt >= end_interval:
                        continue
                    start_dt = max(start_dt, start_interval)
                    end_dt = min(end_dt, end_interval)
                    end_dt = min(end_dt, start_dt + timedelta(hours=to_allocate * (100.0 / allocable)))
                    to_allocate -= ((end_dt - start_dt).total_seconds() / 3600.0) * (allocable / 100.0)
                    self._add_slot_to_list(start_dt, end_dt, resource, following_slots_vals_list, allocable=allocable)
            else:
                end_dt = min(start_interval + timedelta(hours=to_allocate), end_interval)
                to_allocate -= (end_dt - start_interval).total_seconds() / 3600.0
                self._add_slot_to_list(start_interval, end_dt, resource, following_slots_vals_list)

        if float_utils.float_compare(to_allocate, 0.0, precision_digits=2) == 1 and following_slots_vals_list:
            planning_slot_values = self.sale_line_id._planning_slot_values()
            planning_slot_values.update(allocated_hours=to_allocate)
            following_slots_vals_list.append(planning_slot_values)

        return following_slots_vals_list

    def _add_slot_to_list(self, start_datetime, end_datetime, resource, following_slots_vals_list, allocable=100.0):
        if end_datetime <= start_datetime:
            return
        allocated_hours = ((end_datetime - start_datetime).total_seconds() / 3600.0) * (allocable / 100.0)
        following_slots_vals_list.append({
            **self.sale_line_id._planning_slot_values(),
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'allocated_percentage': allocable,
            'allocated_hours': allocated_hours,
            'resource_id': resource.id,
        })

    def _get_resource_work_info(self, vals, slot_vals_list_per_resource):
        """
            This method returns the resource work intervals and a dict representing
            the work_intervals which has conflicting partial slots (slot with allocated percentage < 100.0).

            It retrieves the work intervals and removes the intervals where a complete
            slot exists (allocated_percentage == 100.0).
            It takes into account the slots already added to the vals list.

            :param vals: the vals dict passed to the write method
            :param slot_vals_list_per_resource: a dict with the vals list that will be passed to the create method - sorted per key:resource_id
        """
        self.ensure_one()
        assert self.env.context.get('default_end_datetime')
        if isinstance(vals['start_datetime'], str):
            start_dt = pytz.utc.localize(datetime.strptime(vals['start_datetime'], DEFAULT_SERVER_DATETIME_FORMAT))
        else:
            start_dt = pytz.utc.localize(vals['start_datetime'])
        end_dt = pytz.utc.localize(datetime.strptime(self.env.context['default_end_datetime'], DEFAULT_SERVER_DATETIME_FORMAT))
        # retrieve the resource and its calendar validity intervals
        resource_calendar_validity_intervals, resource = self._get_slot_calendar_and_resource(vals, start_dt, end_dt)
        attendance_intervals = Intervals()
        unavailability_intervals = Intervals()
        # retrieves attendances and unavailabilities of the resource
        for calendar, validity_intervals in resource_calendar_validity_intervals.items():
            attendance = calendar._attendance_intervals_batch(
                start_dt, end_dt, resources=resource)[resource.id]
            leaves = calendar._leave_intervals_batch(
                start_dt, end_dt, resources=resource)[resource.id]
            # The calendar is valid only during its validity interval (see resource_resource:_get_calendars_validity_within_period)
            attendance_intervals |= attendance & validity_intervals
            unavailability_intervals |= leaves & validity_intervals
        partial_slots = {}
        partial_interval_slots = defaultdict(list)
        if resource:
            # gets slots which exists in the period [start_dt;end_dt]
            slots = self.search_read([
                ('resource_id', '=', resource.id),
                ('start_datetime', '<', end_dt.replace(tzinfo=None)),
                ('end_datetime', '>', start_dt.replace(tzinfo=None)),
            ], ['start_datetime', 'end_datetime', 'allocated_percentage'])
            # add the vals list of the resource (slots that will be created at the end of the write method.)
            slots += slot_vals_list_per_resource[resource]
            planning_slots_intervals = Intervals()
            partial_slots = []
            # generate partial intervals and complete intervals
            for slot in slots:
                if not slot['start_datetime']:
                    # this slot is a future unscheduled slots coming from the slot_vals_list_per_resource[resource]
                    continue
                if float_utils.float_compare(slot['allocated_percentage'], 100.0, precision_digits=0) < 0:
                    partial_slots.append(slot)
                else:
                    interval = Intervals([(
                        pytz.utc.localize(slot['start_datetime']),
                        pytz.utc.localize(slot['end_datetime']),
                        self.env['resource.calendar.leaves']
                    )])
                    planning_slots_intervals |= interval
            # adds the full planning_slots to the unavailibility intervals
            unavailability_intervals |= planning_slots_intervals
            work_intervals = attendance_intervals - unavailability_intervals
            if partial_slots:
                # for the partial slots, add it to a list with key = interval, value = list of slots which exists during the interval (at least during a while).
                for interval in work_intervals:
                    # for each interval, add partial slots that conflict.
                    for slot in partial_slots:
                        if pytz.utc.localize(slot['start_datetime']) < interval[1] and pytz.utc.localize(slot['end_datetime']) > interval[0]:
                            partial_interval_slots[interval].append(slot)
        else:
            work_intervals = attendance_intervals - unavailability_intervals
        return work_intervals, unavailability_intervals, resource, partial_interval_slots

    def _get_slot_calendar_and_resource(self, vals, start, end):
        """
            This method is meant to access easily to slot's resource and the resource's calendars with their validity
        """
        self.ensure_one()
        resource = self.resource_id
        if vals.get('resource_id'):
            resource = self.env['resource.resource'].browse(vals.get('resource_id'))
        resource_calendar_validity_intervals = resource._get_calendars_validity_within_period(start, end, default_company=self.company_id)[resource.id]
        return resource_calendar_validity_intervals, resource

    # -------------------------------------------
    # Slots Assignation
    # -------------------------------------------

    @api.model
    def _get_employee_to_assign_priority_list(self):
        return ['previous_slot', 'default_role', 'roles']

    def _get_employee_per_priority(self, priority, employee_ids_to_exclude, cache):
        """
            This method returns the id of an employee filling the priority criterias and
            not present in the employee_ids_to_exclude.
        """
        if priority in cache:
            return cache[priority].pop(0) if cache.get(priority) else None
        if priority == 'previous_slot':
            search = self._read_group([
                ('sale_line_id', '=', self.sale_line_id.id),
                ('employee_id', '!=', False),
                ('start_datetime', '!=', False),
                ('employee_id', 'not in', employee_ids_to_exclude),
            ], ['employee_id'], order='end_datetime:max desc, employee_id')
            cache[priority] = [employee.id for [employee] in search]
        elif priority == 'default_role':
            search = self.env['hr.employee'].sudo().search([
                ('default_planning_role_id', '=', self.role_id.id),
                ('id', 'not in', employee_ids_to_exclude),
            ])
            cache[priority] = search.ids
        elif priority == 'roles':
            search = self.env['hr.employee'].search([
                ('planning_role_ids', '=', self.role_id.id),
                ('id', 'not in', employee_ids_to_exclude),
            ])
            cache[priority] = search.ids
        return cache[priority].pop(0) if cache.get(priority) else None

    def _get_employee_to_assign(self, default_priority, employee_ids_to_exclude, cache, employee_per_sol):
        """
            Returns the id of the employee to assign and its corresponding priority
        """
        self.ensure_one()
        if self.sale_line_id.id in employee_per_sol:
            employee_id = next(
                (employee_id
                 for employee_id in employee_per_sol[self.sale_line_id.id]
                 if employee_id not in employee_ids_to_exclude),
                None
            )
            return employee_id, default_priority
        # This method is written to be overridden, so as every module can keep the priority ordered as its required.
        priority_list = self._get_employee_to_assign_priority_list()
        for priority in priority_list:
            if not default_priority or priority == default_priority:
                # if default_priority is given, the search only starts with this priority.
                default_priority = None
                employee_id = self._get_employee_per_priority(priority, employee_ids_to_exclude, cache)
                if employee_id:
                    return employee_id, priority
        return None, None

    @api.model
    def _get_ordered_slots_to_assign(self, domain):
        """
            Returns an ordered list of slots (linked to sol) to plan while using the action_plan_sale_order.

            This method is meant to be easily overriden.
        """
        return self.search(domain, order='sale_line_id desc')

    @api.model
    def _get_employee_per_sol_within_period(self, slots, start, end):
        """ Gets the employees already assigned during this period.

            :returns: a dict with key : SOL id, and values : a list of employee ids
        """
        assert start and end
        if isinstance(end, str):
            end = datetime.strptime(end, DEFAULT_SERVER_DATETIME_FORMAT)

        employee_per_sol = self.env['planning.slot']._read_group([
            ('sale_line_id', 'in', slots.sale_line_id.ids),
            ('start_datetime', '<', end),
            ('end_datetime', '>', start),
            ('employee_id', '!=', False),
        ], ['sale_line_id'], ['employee_id:array_agg'])

        return {
            sale_line.id: employee_ids
            for sale_line, employee_ids in employee_per_sol
        }

    def _get_shifts_to_plan_domain(self, view_domain=None):
        new_view_domain = []
        if view_domain:
            for clause in view_domain:
                if isinstance(clause, str) or clause[0] not in ['start_datetime', 'end_datetime']:
                    new_view_domain.append(clause)
                elif clause[0] in ['start_datetime', 'end_datetime']:
                    new_view_domain.append([clause[0], '=', False])
        else:
            new_view_domain = [('start_datetime', '=', False)]
        domain = expression.AND([new_view_domain, [('sale_line_id', '!=', False)]])
        if self.env.context.get('planning_gantt_active_sale_order_id'):
            domain = expression.AND([domain, [('sale_order_id', '=', self.env.context.get('planning_gantt_active_sale_order_id'))]])
        return domain

    @api.model
    def auto_plan_ids(self, view_domain):
        res = super(PlanningSlot, self).auto_plan_ids(view_domain)
        if self._context.get('planning_slot_id'):
            # It means we are looking to assign one shift in particular to an available resource, which we do in planning.
            return res
        slots_to_assign = self._get_ordered_slots_to_assign(self._get_shifts_to_plan_domain(view_domain))
        start_datetime = max(datetime.strptime(self.env.context.get('default_start_datetime'), DEFAULT_SERVER_DATETIME_FORMAT), fields.Datetime.now().replace(hour=0, minute=0, second=0))
        employee_per_sol = self._get_employee_per_sol_within_period(slots_to_assign, start_datetime, self.env.context.get('default_end_datetime'))
        PlanningShift = self.env['planning.slot']
        slots_assigned = PlanningShift
        employee_ids_to_exclude = []
        for slot in slots_to_assign:
            slot_assigned = PlanningShift
            previous_priority = None
            cache = {}
            while not slot_assigned:
                # Retrieve an employee_id that may be assigned to this slot, excluding the ones who have no time left.
                # The previous priority is given in order to get the second employee that respects the previous criterias
                employee_id, previous_priority = slot._get_employee_to_assign(previous_priority, employee_ids_to_exclude, cache, employee_per_sol)
                if not employee_id:
                    break
                # The browse is mandatory to access the resource calendar
                employee = self.env['hr.employee'].browse(employee_id)
                vals = {
                    'start_datetime': start_datetime,
                    'end_datetime': start_datetime + timedelta(days=1),
                    'resource_id': employee.resource_id.id
                }
                # With the context keys, the maximal date to assign the slot will be self.env.context.get('default_end_datetime')
                slot_assigned = slot.assign_slot(vals)
                if not slot_assigned:
                    # if no slot was generated (it uses the write method), then the employee_id is excluded from the employees assignable on this slot.
                    employee_ids_to_exclude.append(employee_id)
            slots_assigned += slot_assigned
        return res + slots_assigned.ids

    # -------------------------------------------
    # Copy slots
    # -------------------------------------------

    def _init_remaining_hours_to_plan(self, remaining_hours_to_plan):
        """
            Fills the remaining_hours_to_plan dict for a given slot and returns wether
            there are enough remaining hours.

            :return a bool representing wether or not there are still hours remaining
        """
        self.ensure_one()
        res = super()._init_remaining_hours_to_plan(remaining_hours_to_plan)
        if self.sale_line_id.product_id.planning_enabled:
            # if the slot is linked to a slot, we only need to allocate the remaining hours to plan
            # we keep track of those hours in a dict and decrease it each time we create a slot.
            if self.sale_line_id not in remaining_hours_to_plan:
                self.sale_line_id._compute_planning_hours_planned()
                remaining_hours_to_plan[self.sale_line_id] = self.sale_line_id.planning_hours_to_plan - self.sale_line_id.planning_hours_planned
            if float_utils.float_compare(remaining_hours_to_plan[self.sale_line_id], 0.0, precision_digits=2) != 1:
                return False  # nothing left to allocate.
        return res

    def _update_remaining_hours_to_plan_and_values(self, remaining_hours_to_plan, values):
        """
            Update the remaining_hours_to_plan with the allocated hours of the slot in `values`
            and returns wether there are enough remaining hours.

            If remaining_hours is strictly positive, and the allocated hours of the slot in `values` is
            higher than remaining hours, than update the values in order to consume at most the
            number of remaining_hours still available.

            :return a bool representing wether or not there are still hours remaining
        """
        if self.allocated_percentage and self.sale_line_id.product_id.planning_enabled:
            if float_utils.float_compare(remaining_hours_to_plan[self.sale_line_id], 0.0, precision_digits=2) != 1:
                return False
            # The allocated hours of the slot can be computed as for a slot with allocation_type == 'planning'
            # since it is build from an employee work interval, thus will last less than 24hours.
            allocated_hours = (values['end_datetime'] - values['start_datetime']).total_seconds() / 3600
            # Allocated_hours is discounted from remaining hours with a maximum of : remaining_hours
            # So, the difference between the two values must be checked, if remaining_hours is less than the
            # allocated hours, than update the end_datetime.
            ratio = self.allocated_percentage / 100.00
            remaining_hours = min(remaining_hours_to_plan[self.sale_line_id] / ratio, allocated_hours)
            values['end_datetime'] = values['start_datetime'] + timedelta(hours=remaining_hours)
            values.pop('allocated_hours', None) # we want that to be computed again.
            remaining_hours_to_plan[self.sale_line_id] -= remaining_hours * ratio
        return True

    def action_unschedule(self):
        self.ensure_one()
        if self.sale_line_id.product_id.planning_enabled:
            if self.sale_line_id.planning_hours_to_plan - self.sale_line_id.planning_hours_planned > 0.0:
                unscheduled_slot = self.search([
                    ('sale_line_id', '=', self.sale_line_id.id),
                    ('start_datetime', '=', False),
                ])
                if unscheduled_slot:
                    self.unlink()
                    return {'type': 'ir.actions.act_window_close'}
        return self.write({
            'start_datetime': False,
            'end_datetime': False,
            'employee_id': False,
        })

    # -----------------------------------
    # Gantt Progress Bar
    # -----------------------------------
    def _gantt_progress_bar_sale_line_id(self, res_ids):
        if not self.env['sale.order.line'].check_access_rights('read', raise_exception=False):
            return {}
        return {
            sol.id: {
                'value': sol.planning_hours_planned,
                'max_value': sol.planning_hours_to_plan,
            }
            for sol in self.env['sale.order.line'].search([('id', 'in', res_ids)])
        }

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'sale_line_id':
            return dict(
                self._gantt_progress_bar_sale_line_id(res_ids),
                warning=_("This Sale Order Item doesn't have a target value of planned hours. Planned hours :")
            )
        return super()._gantt_progress_bar(field, res_ids, start, stop)

    def _prepare_shift_vals(self):
        return {
            **super()._prepare_shift_vals(),
            'sale_line_id': self.sale_line_id.id,
        }

    def _gantt_progress_bar_resource_id(self, res_ids, start, stop):
        results = super()._gantt_progress_bar_resource_id(res_ids, start, stop)
        resource_per_id = {r.id: r for r in self.env['resource.resource'].browse(list(results.keys()))}
        for key, val in results.items():
            resource = resource_per_id[key]
            val['role_ids'] = resource.role_ids.ids
        return results
