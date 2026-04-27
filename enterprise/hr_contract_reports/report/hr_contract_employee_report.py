# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class HrContractEmployeeReport(models.Model):
    _name = "hr.contract.employee.report"
    _description = "Contract and Employee Analysis Report"
    _auto = False
    _rec_name = 'date'

    contract_id = fields.Many2one('hr.contract', 'Contract', readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    department_id = fields.Many2one('hr.department', 'Department', readonly=True)

    employee_count = fields.Integer('# Employees')
    count_employee_exit = fields.Integer('# Departure Employee', readonly=True)
    count_new_employee = fields.Integer('# New Employees', readonly=True)
    age_sum = fields.Float('Duration Contract', aggregator="sum", readonly=True)

    wage = fields.Float('Wage', aggregator="avg", readonly=True)

    date = fields.Date('Date', readonly=True)
    start_date_months = fields.Integer("Months of first date of this month since 01/01/1970", readonly=True)
    end_date_months = fields.Integer("Months of last date of this month since 01/01/1970", readonly=True)
    date_end_contract = fields.Date('Date Last Contract Ended', aggregator="max", readonly=True)
    contract_start = fields.Date('Date First Contract Started', aggregator="min", readonly=True)

    departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason", readonly=True)

    def _query(self, fields='', from_clause='', outer=''):
        select_ = '''
            c.id as id,
            c.id as contract_id,
            e.id as employee_id,
            1 as employee_count,
            e.company_id as company_id,
            e.departure_reason_id as departure_reason_id,
            e.department_id as department_id,
            c.wage AS wage,
            CASE WHEN serie = start.contract_start THEN 1 ELSE 0 END as count_new_employee,
            CASE WHEN exit.contract_end IS NOT NULL AND date_part('month', exit.contract_end) = date_part('month', serie) AND date_part('year', exit.contract_end) = date_part('year', serie) THEN 1 ELSE 0 END as count_employee_exit,
            c.date_start,
            c.date_end,
            exit.contract_end as date_end_contract,
            start.contract_start,
            CASE
                WHEN date_part('month', c.date_start) = date_part('month', serie) AND date_part('year', c.date_start) = date_part('year', serie)
                    THEN (31 - LEAST(date_part('day', c.date_start), 30)) / 30
                WHEN c.date_end IS NULL THEN 1
                WHEN date_part('month', c.date_end) = date_part('month', serie) AND date_part('year', c.date_end) = date_part('year', serie)
                    THEN (LEAST(date_part('day', c.date_end), 30) / 30)
                ELSE 1 END as age_sum,
            serie::DATE as date,
            EXTRACT(EPOCH FROM serie)/2628028.8 AS start_date_months, -- 2628028.8 = 3600 * 24 * 30.417 (30.417 is the mean number of days in a month)
            CASE
                WHEN c.date_end IS NOT NULL AND date_part('month', c.date_end) = date_part('month', serie) AND date_part('year', c.date_end) = date_part('year', serie) THEN
                    EXTRACT(EPOCH FROM (c.date_end))/2628028.8
                ELSE
                    EXTRACT(EPOCH FROM (date_trunc('month', serie) + interval '1 month' - interval '1 day'))/2628028.8
                END AS end_date_months

            %s
        ''' % fields

        from_ = """
                (SELECT age(COALESCE(date_end, current_date), date_start) as age, * FROM hr_contract WHERE state != 'cancel' and active IS TRUE and employee_id IS NOT NULL) c
                LEFT JOIN hr_employee e ON (e.id = c.employee_id)
                LEFT JOIN (
                    SELECT employee_id, contract_end
                    FROM (SELECT employee_id, CASE WHEN array_position(array_agg(date_end), NULL) IS NOT NULL THEN NULL ELSE max(date_end) END as contract_end FROM hr_contract WHERE state != 'cancel' GROUP BY employee_id) c_end
                    WHERE c_end.contract_end <= current_date) exit on (exit.employee_id = c.employee_id)
                LEFT JOIN (
                    SELECT employee_id, MIN(date_start) as contract_start
                    FROM hr_contract WHERE state != 'cancel'
                    GROUP BY employee_id) start on (start.employee_id = c.employee_id)
                 %s
                CROSS JOIN generate_series(c.date_start, (CASE WHEN c.date_end IS NULL THEN current_date + interval '1 year' ELSE (CASE WHEN date_part('day', c.date_end) < date_part('day', c.date_start) THEN c.date_end + interval '1 month' ELSE c.date_end END) END), interval '1 month') serie
        """ % from_clause

        return '(SELECT * %s FROM (SELECT %s FROM %s) in_query)' % (outer, select_, from_)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
