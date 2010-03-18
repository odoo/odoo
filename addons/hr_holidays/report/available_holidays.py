from osv import fields,osv
import tools

class hr_holidays_report(osv.osv):
    _name = "hr.holidays.report"
    _auto = False
    _columns = {
        'employee_id': fields.many2one ('hr.employee', 'Employee', readonly=True),
        'holiday_status_id': fields.many2one('hr.holidays.status', 'Leave Type', readonly=True),
 #       'max_leave': fields.float('Allocated Leaves', readonly=True),
#        'taken_leaves': fields.float('Taken Leaves', readonly=True),
        'remaining_leave': fields.float('Remaining Leaves',readonly=True), 
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_holidays_report')
        cr.execute("""
            create or replace view hr_holidays_report as (
                select
                    min(h.id) as id,
                    h.employee_id as employee_id,
                    h.holiday_status_id as holiday_status_id,
                    sum(number_of_days) as remaining_leave
                from
                    hr_holidays h
                left join hr_holidays_status s on (s.id = h.holiday_status_id)
                where h.state = 'validate'
                and h.employee_id is not null
                and s.active <> 'f'
                group by h.holiday_status_id, h.employee_id
            )""")
hr_holidays_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
