# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.osv import fields, osv


class hr_evaluation_report(osv.Model):
    _name = "hr.evaluation.report"
    _description = "Evaluations Statistics"
    _auto = False
    _columns = {
        'create_date': fields.datetime('Create Date', readonly=True),
        'delay_date': fields.float('Delay to Start', digits=(16, 2), readonly=True),
        'overpass_delay': fields.float('Overpassed Deadline', digits=(16, 2), readonly=True),
        'deadline': fields.date("Deadline", readonly=True),
        'request_id': fields.many2one('survey.user_input', 'Request ID', readonly=True),
        'closed': fields.date("Close Date", readonly=True),  # TDE FIXME master: rename into date_close
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', readonly=True),
        'employee_id': fields.many2one('hr.employee', "Employee", readonly=True),
        'rating': fields.selection([
            ('0', 'Significantly bellow expectations'),
            ('1', 'Did not meet expectations'),
            ('2', 'Meet expectations'),
            ('3', 'Exceeds expectations'),
            ('4', 'Significantly exceeds expectations'),
        ], "Overall Rating", readonly=True),
        'nbr': fields.integer('# of Requests', readonly=True),  # TDE FIXME master: rename into nbr_requests
        'state': fields.selection([
            ('draft', 'Draft'),
            ('wait', 'Plan In Progress'),
            ('progress', 'Final Validation'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ], 'Status', readonly=True),
    }
    _order = 'create_date desc'

    _depends = {
        'hr.evaluation.interview': ['evaluation_id', 'id', 'request_id'],
        'hr_evaluation.evaluation': [
            'create_date', 'date', 'date_close', 'employee_id', 'plan_id',
            'rating', 'state',
        ],
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_evaluation_report')
        cr.execute("""
            create or replace view hr_evaluation_report as (
                 select
                     min(l.id) as id,
                     s.create_date as create_date,
                     s.employee_id,
                     l.request_id,
                     s.plan_id,
                     s.rating,
                     s.date as deadline,
                     s.date_close as closed,
                     count(l.*) as nbr,
                     s.state,
                     avg(extract('epoch' from age(s.create_date,CURRENT_DATE)))/(3600*24) as  delay_date,
                     avg(extract('epoch' from age(s.date,CURRENT_DATE)))/(3600*24) as overpass_delay
                     from
                 hr_evaluation_interview l
                LEFT JOIN
                     hr_evaluation_evaluation s on (s.id=l.evaluation_id)
                 GROUP BY
                     s.create_date,
                     s.state,
                     s.employee_id,
                     s.date,
                     s.date_close,
                     l.request_id,
                     s.rating,
                     s.plan_id
            )
        """)
