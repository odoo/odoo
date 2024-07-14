# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, tools
from odoo import fields, models

from psycopg2 import sql

class PlanningAnalysisReport(models.Model):
    _name = "planning.analysis.report"
    _description = "Planning Analysis Report"
    _auto = False

    allocated_hours = fields.Float("Allocated Hours", readonly=True)
    allocated_percentage = fields.Float("Allocated Time (%)", readonly=True, group_operator="avg")
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    department_id = fields.Many2one("hr.department", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    end_datetime = fields.Datetime("End Date", readonly=True)
    job_title = fields.Char("Job Title", readonly=True)
    manager_id = fields.Many2one("hr.employee", string="Manager", readonly=True)
    name = fields.Text("Note", readonly=True)
    publication_warning = fields.Boolean(
        "Modified Since Last Publication", readonly=True,
        help="If checked, it means that the shift contains has changed since its last publish.")
    recurrency_id = fields.Many2one("planning.recurrency", readonly=True)
    resource_id = fields.Many2one("resource.resource", string="Resource", readonly=True)
    resource_type = fields.Selection([
        ("user", "Human"),
        ("material", "Material")], string="Type",
        default="user", readonly=True)
    role_id = fields.Many2one("planning.role", string="Role", readonly=True)
    start_datetime = fields.Datetime("Start Date", readonly=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("published", "Published"),
    ], string="Status", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    working_days_count = fields.Float("Working Days", readonly=True)
    slot_id = fields.Many2one("planning.slot", string="Planning Slot", readonly=True)
    request_to_switch = fields.Boolean('Has there been a request to switch on this shift slot?', readonly=True)

    @property
    def _table_query(self):
        return "%s %s %s %s" % (self._select(), self._from(), self._join(), self._group_by())

    @api.model
    def _select(self):
        return """
            SELECT
                S.id AS id,
                S.id AS slot_id,
                S.allocated_hours AS allocated_hours,
                S.allocated_percentage AS allocated_percentage,
                S.company_id AS company_id,
                S.department_id AS department_id,
                S.employee_id AS employee_id,
                S.end_datetime AS end_datetime,
                E.job_title AS job_title,
                S.manager_id AS manager_id,
                S.name AS name,
                S.publication_warning AS publication_warning,
                S.request_to_switch AS request_to_switch,
                S.resource_id AS resource_id,
                R.resource_type AS resource_type,
                S.role_id AS role_id,
                S.recurrency_id AS recurrency_id,
                S.start_datetime AS start_datetime,
                S.state AS state,
                S.user_id AS user_id,
                S.working_days_count AS working_days_count
        """

    @api.model
    def _from(self):
        return """
            FROM planning_slot S
        """

    @api.model
    def _join(self):
        return """
            LEFT JOIN hr_employee E ON E.id = S.employee_id
            LEFT JOIN resource_resource R ON R.id = S.resource_id
        """

    @api.model
    def _group_by(self):
        return """
            GROUP BY S.id,
                     S.allocated_hours,
                     S.allocated_percentage,
                     S.company_id,
                     S.department_id,
                     S.employee_id,
                     S.end_datetime,
                     E.job_title,
                     S.manager_id,
                     S.name,
                     S.publication_warning,
                     S.resource_id,
                     R.resource_type,
                     S.role_id,
                     S.recurrency_id,
                     S.start_datetime,
                     S.state,
                     S.user_id,
                     S.working_days_count
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(self._table_query)
            )
        )
