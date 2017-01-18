# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ProjectIssueReport(models.Model):
    _name = "project.issue.report"
    _auto = False

    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    opening_date = fields.Datetime('Date of Opening', readonly=True)
    create_date = fields.Datetime('Create Date', readonly=True)
    date_closed = fields.Datetime('Date of Closing', readonly=True)
    date_last_stage_update = fields.Datetime('Last Stage Update', readonly=True)
    stage_id = fields.Many2one('project.task.type', 'Stage')
    nbr_issues = fields.Integer('# of Issues', readonly=True)
    working_hours_open = fields.Float('Avg. Working Hours to Open', readonly=True, group_operator="avg")
    working_hours_close = fields.Float('Avg. Working Hours to Close', readonly=True, group_operator="avg")
    delay_open = fields.Float('Avg. Delay to Open', digits=(16, 2), readonly=True, group_operator="avg",
                              help="Number of Days to open the project issue.")
    delay_close = fields.Float('Avg. Delay to Close', digits=(16, 2), readonly=True, group_operator="avg",
                               help="Number of Days to close the project issue")
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')])
    project_id = fields.Many2one('project.project', 'Project', readonly=True)
    user_id = fields.Many2one('res.users', 'Assigned to', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Contact')
    email = fields.Integer('# Emails', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'project_issue_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW project_issue_report AS (
                SELECT
                    c.id as id,
                    c.date_open as opening_date,
                    c.create_date as create_date,
                    c.date_last_stage_update as date_last_stage_update,
                    c.user_id,
                    c.working_hours_open,
                    c.working_hours_close,
                    c.stage_id,
                    c.date_closed as date_closed,
                    c.company_id as company_id,
                    c.priority as priority,
                    c.project_id as project_id,
                    1 as nbr_issues,
                    c.partner_id,
                    c.day_open as delay_open,
                    c.day_close as delay_close,
                    (SELECT count(id) FROM mail_message WHERE model='project.issue' AND message_type IN ('email', 'comment') AND res_id=c.id) AS email

                FROM
                    project_issue c
                LEFT JOIN project_task t on c.task_id = t.id
                WHERE c.active= 'true'
            )""")
