# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _description = "Leave Type"

    def get_days(self, cr, uid, ids, employee_id, context=None):
        result = dict((id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0,
                                virtual_remaining_leaves=0)) for id in ids)
        holiday_ids = self.pool['hr.holidays'].search(cr, uid, [('employee_id', '=', employee_id),
                                                                ('state', 'in', ['confirm', 'validate1', 'validate']),
                                                                ('holiday_status_id', 'in', ids)
                                                                ], context=context)
        for holiday in self.pool['hr.holidays'].browse(cr, uid, holiday_ids, context=context):
            status_dict = result[holiday.holiday_status_id.id]
            if holiday.type == 'add':
                if holiday.state == 'validate':
                    # note: add only validated allocation even for the virtual
                    # count; otherwise pending then refused allocation allow
                    # the employee to create more leaves than possible
                    status_dict['virtual_remaining_leaves'] += holiday.number_of_days_temp
                    status_dict['max_leaves'] += holiday.number_of_days_temp
                    status_dict['remaining_leaves'] += holiday.number_of_days_temp
            elif holiday.type == 'remove':  # number of days is negative
                status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
                if holiday.state == 'validate':
                    status_dict['leaves_taken'] += holiday.number_of_days_temp
                    status_dict['remaining_leaves'] -= holiday.number_of_days_temp
        return result

    def _user_left_days(self, cr, uid, ids, name, args, context=None):
        employee_id = False
        if context and 'employee_id' in context:
            employee_id = context['employee_id']
        else:
            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
            if employee_ids:
                employee_id = employee_ids[0]
        if employee_id:
            res = self.get_days(cr, uid, ids, employee_id, context=context)
        else:
            res = dict((res_id, {'leaves_taken': 0, 'remaining_leaves': 0, 'max_leaves': 0}) for res_id in ids)
        return res

    _columns = {
        'name': fields.char('Leave Type', size=64, required=True, translate=True),
        'categ_id': fields.many2one('calendar.event.type', 'Meeting Type',
            help='Once a leave is validated, Odoo will create a corresponding meeting of this type in the calendar.'),
        'color_name': fields.selection([('red', 'Red'),('blue','Blue'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color in Report', required=True, help='This color will be used in the leaves summary located in Reporting\Leaves by Department.'),
        'limit': fields.boolean('Allow to Override Limit', help='If you select this check box, the system allows the employees to take more leaves than the available ones for this type and will not take them into account for the "Remaining Legal Leaves" defined on the employee form.'),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the leave type without removing it."),
        'max_leaves': fields.function(_user_left_days, string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', multi='user_left_days'),
        'leaves_taken': fields.function(_user_left_days, string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.', multi='user_left_days'),
        'remaining_leaves': fields.function(_user_left_days, string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken', multi='user_left_days'),
        'virtual_remaining_leaves': fields.function(_user_left_days, string='Virtual Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval', multi='user_left_days'),
        'double_validation': fields.boolean('Apply Double Validation', help="When selected, the Allocation/Leave Requests for this type require a second validation to be approved."),
    }
    _defaults = {
        'color_name': 'red',
        'active': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(hr_holidays_status, self).name_get(cr, uid, ids, context=context)
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if not record.limit:
                name = name + ('  (%g/%g)' % (record.virtual_remaining_leaves or 0.0, record.max_leaves or 0.0))
            res.append((record.id, name))
        return res

    def _search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        """ Override _search to order the results, according to some employee.
        The order is the following

         - limit (limited leaves first, such as Legal Leaves)
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method. """
        if context is None:
            context = {}
        ids = super(hr_holidays_status, self)._search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count, access_rights_uid=access_rights_uid)
        if not count and not order and context.get('employee_id'):
            leaves = self.browse(cr, uid, ids, context=context)
            sort_key = lambda l: (not l.limit, l.virtual_remaining_leaves)
            return map(int, leaves.sorted(key=sort_key, reverse=True))
        return ids

    def compute_holidays(self, employee_id):
        holidays = self.env['hr.holidays'].search([
            ('employee_id', '=', employee_id),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', '=', self.id)
        ])
        print "emp_id___________", employee_id
        for holiday in holidays:
            print "temp_______________", holiday.number_of_days_temp
            if holiday.holiday_status_id.id == self.id:
                if holiday.request_type == 'add':
                    if holiday.state == 'validate':
                        self.virtual_remaining_leaves += holiday.number_of_days_temp
                        self.max_leaves += holiday.number_of_days_temp
                        self.remaining_leaves += holiday.number_of_days_temp
                elif holiday.request_type == 'remove':  # number of days is negative
                    self.virtual_remaining_leaves -= holiday.number_of_days_temp
                    if holiday.state == 'validate':
                        self.leaves_taken += holiday.number_of_days_temp
                        self.remaining_leaves -= holiday.number_of_days_temp
        print "1_______________", self.virtual_remaining_leaves
        print "2_______________", self.max_leaves
        print "3_______________", self.remaining_leaves
        print "4_______________", self.leaves_taken


    # def compute_holidays(self, employee_id):
    #     holidays = self.env['hr.holidays'].search([
    #         ('employee_id', '=', employee_id),
    #         ('state', 'in', ['confirm', 'validate1', 'validate']),
    #         ('holiday_status_id', '=', self.id)
    #     ])
    #     print "emp_id___________", employee_id
    #     for holiday in holidays.filtered(
    #             lambda h: h.holiday_status_id.id == self.id and
    #             h.request_type == 'add' and
    #             h.state == 'validate'):
    #         self.virtual_remaining_leaves += holiday.number_of_days_temp
    #         self.max_leaves += holiday.number_of_days_temp
    #         self.remaining_leaves += holiday.number_of_days_temp

    #     for holiday in holidays.filtered(
    #             lambda h: h.holiday_status_id.id == self.id and
    #             h.request_type == 'remove'):    # number of days is negative
    #         self.virtual_remaining_leaves -= holiday.number_of_days_temp
    #         if holiday.state == 'validate':
    #             self.leaves_taken += holiday.number_of_days_temp
    #             self.remaining_leaves -= holiday.number_of_days_temp
    #     print "1_______________", self.virtual_remaining_leaves
    #     print "2_______________", self.max_leaves
    #     print "3_______________", self.remaining_leaves
    #     print "4_______________", self.leaves_taken
>>>>>>> a286ecb... a
