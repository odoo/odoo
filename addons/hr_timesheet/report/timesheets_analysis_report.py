# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class TimesheetsAnalysisReport(models.Model):
    _name = "timesheets.analysis.report"
    _inherit = "hr.manager.department.report"
    _description = "Timesheets Analysis Report"
    _auto = False

    name = fields.Char("Description", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    task_id = fields.Many2one("project.task", string="Task", readonly=True)
    parent_task_id = fields.Many2one("project.task", string="Parent Task", readonly=True)
    manager_id = fields.Many2one("hr.employee", "Manager", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    date = fields.Date("Date", readonly=True)
    amount = fields.Monetary("Amount", currency_field="currency_id", readonly=True)
    unit_amount = fields.Float("Time Spent", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", readonly=True)
    milestone_id = fields.Many2one('project.milestone', related='task_id.milestone_id')
    message_partner_ids = fields.Many2many('res.partner', compute='_compute_message_partner_ids',
                                           search='_search_message_partner_ids', readonly=True)

    @api.depends('project_id.message_partner_ids', 'task_id.message_partner_ids')
    def _compute_message_partner_ids(self):
        for line in self:
            line.message_partner_ids = line.task_id.message_partner_ids | line.project_id.message_partner_ids

    def _search_message_partner_ids(self, operator, value):
        return self.env['account.analytic.line']._search_message_partner_ids(operator, value)

    @property
    def _table_query(self):
        return "%s %s %s" % (self._select(), self._from(), self._where())

    @api.model
    def _select(self):
        return """
            SELECT
                A.id AS id,
                A.name AS name,
                A.user_id AS user_id,
                A.project_id AS project_id,
                A.task_id AS task_id,
                A.parent_task_id AS parent_task_id,
                A.employee_id AS employee_id,
                A.manager_id AS manager_id,
                A.company_id AS company_id,
                A.department_id AS department_id,
                A.currency_id AS currency_id,
                A.date AS date,
                A.amount AS amount,
                A.unit_amount AS unit_amount,
                A.partner_id AS partner_id
        """

    @api.model
    def _from(self):
        return "FROM account_analytic_line A"

    @api.model
    def _where(self):
        return "WHERE A.project_id IS NOT NULL"

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""CREATE or REPLACE VIEW %s as (%s)""", SQL.identifier(self._table), SQL(self._table_query)))
