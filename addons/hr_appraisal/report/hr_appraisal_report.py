# -*- coding: utf-8 -*-

from openerp import fields, models, tools


class HrAppraisalReport(models.Model):
    _name = "hr.appraisal.report"
    _description = "Appraisal Statistics"
    _auto = False

    create_date = fields.Date(string='Create Date', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department')
    delay_date = fields.Float(string='Delay to Start', digits=(16, 2), readonly=True)
    overpass_delay = fields.Float(string='Overpassed Deadline', digits=(16, 2), readonly=True)
    deadline = fields.Date(string="Deadline", readonly=True)
    final_interview = fields.Date(string="Interview", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    nbr = fields.Integer(string='# of Requests', readonly=True)  # TDE FIXME master: rename into nbr_requests
    state = fields.Selection([
        ('new', 'To Start'),
        ('pending', 'Appraisal Sent'),
        ('done', 'Done')
    ], 'Status', readonly=True)

    _order = 'create_date desc'

    _depends = {
        'hr.appraisal': [
            'create_date', 'interview_deadline', 'date_close', 'employee_id', 'state',
        ],
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_appraisal_report')
        cr.execute("""
            create or replace view hr_appraisal_report as (
                 select
                     min(s.id) as id,
                     date(s.create_date) as create_date,
                     s.employee_id,
                     e.department_id as department_id,
                     s.date_close as deadline,
                     s.interview_deadline as final_interview,
                     count(s.*) as nbr,
                     s.state,
                     avg(extract('epoch' from age(s.create_date,CURRENT_DATE)))/(3600*24) as  delay_date,
                     avg(extract('epoch' from age(s.date_close,CURRENT_DATE)))/(3600*24) as overpass_delay
                     from hr_appraisal s
                        left join hr_employee e on (e.id=s.employee_id)
                 GROUP BY
                     s.id,
                     s.create_date,
                     s.state,
                     s.employee_id,
                     s.date_close,
                     s.interview_deadline,
                     e.department_id
                )
            """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
