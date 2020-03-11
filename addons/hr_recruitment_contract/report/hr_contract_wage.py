# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import fields, models

from odoo.addons.hr_contract.models.hr_contract import CONTRACT_STATES


class HrContractWageReport(models.Model):
    _name = "hr.contract.wage"
    _description = "Contract wage summary"
    _auto = False

    department_id = fields.Many2one("hr.department")
    job_id = fields.Many2one("hr.job")
    resource_calendar_id = fields.Many2one("resource.calendar")
    employee_experience = fields.Float(help="Employee arrival (years)", digits=(10, 1))
    wage = fields.Monetary()
    currency_id = fields.Many2one("res.currency")
    company_id = fields.Many2one("res.company")
    state = fields.Selection(CONTRACT_STATES)

    def _query_fields(self):
        return [
            'row_number() OVER() AS id',
            'c.department_id',
            'c.job_id',
            'c.resource_calendar_id',
            'c.wage',
            'c.company_id',
            'c.state',
            'company.currency_id',
            """ROUND(
                (EXTRACT(EPOCH FROM AGE(e.create_date)) / (60 * 60 * 24 * 365))::numeric,
                1
            ) AS employee_experience""",
        ]

    def _fields_sql(self):
        return ', '.join(self._query_fields())

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE or REPLACE VIEW {table} as (
                SELECT {fields}
                FROM hr_contract AS c
                LEFT JOIN res_company AS company ON company.id = c.company_id
                LEFT JOIN hr_employee AS e ON e.id = c.employee_id
                WHERE c.active = TRUE AND c.employee_id IS NOT NULL
        )""".format(
                table=self._table,
                fields=self._fields_sql(),
            )
        )
