# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY
from odoo.addons.rating.models.rating_data import RATING_LIMIT_MIN


class HelpdeskSLAReport(models.Model):
    _name = 'helpdesk.sla.report.analysis'
    _description = "SLA Status Analysis"
    _auto = False
    _order = 'create_date DESC'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', readonly=True)
    description = fields.Text(readonly=True)
    tag_ids = fields.Many2many('helpdesk.tag', relation='helpdesk_tag_helpdesk_ticket_rel',
        column1='helpdesk_ticket_id', column2='helpdesk_tag_id',
        string='Tags', readonly=True)
    ticket_ref = fields.Char(string='Ticket IDs Sequence', readonly=True)
    name = fields.Char(string='Subject', readonly=True)
    create_date = fields.Datetime("Ticket Create Date", readonly=True)
    priority = fields.Selection(TICKET_PRIORITY, string='Minimum Priority', readonly=True)
    user_id = fields.Many2one('res.users', string="Assigned To", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    partner_name = fields.Char(string='Customer Name', readonly=True)
    partner_email = fields.Char(string='Customer Email', readonly=True)
    partner_phone = fields.Char(string='Customer Phone', readonly=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Type", readonly=True)
    stage_id = fields.Many2one('helpdesk.stage', string="Stage", readonly=True)
    ticket_closed = fields.Boolean("Ticket Closed", readonly=True)
    ticket_close_hours = fields.Integer("Working Hours to Close", group_operator="avg", readonly=True)
    ticket_assignation_hours = fields.Integer("Working Hours to Assign", group_operator="avg", readonly=True)
    close_date = fields.Datetime("Close date", readonly=True)
    sla_id = fields.Many2one('helpdesk.sla', string='SLA', readonly=True)
    sla_ids = fields.Many2many('helpdesk.sla', 'helpdesk_sla_status', 'ticket_id', 'sla_id', string="SLAs", copy=False)
    sla_status_ids = fields.One2many('helpdesk.sla.status', 'ticket_id', string="SLA Status")
    sla_stage_id = fields.Many2one('helpdesk.stage', string="SLA Stage", readonly=True)
    sla_deadline = fields.Datetime("SLA Deadline", group_operator='min', readonly=True)
    sla_status = fields.Selection([('failed', 'SLA Failed'), ('reached', 'SLA Success'), ('ongoing', 'SLA in Progress')], string="Status", readonly=True)
    sla_fail = fields.Boolean("SLA Status Failed", group_operator='bool_or', readonly=True)
    sla_success = fields.Boolean("SLA Status Success", group_operator='bool_or', readonly=True)
    sla_exceeded_hours = fields.Integer("Working Hours to Reach SLA", group_operator='avg', readonly=True, help="Day to reach the stage of the SLA, without taking the working calendar into account")
    sla_status_failed = fields.Integer("Number of SLA Failed", readonly=True)
    active = fields.Boolean("Active", readonly=True)
    rating_last_value = fields.Float("Rating (/5)", group_operator="avg", readonly=True)
    rating_avg = fields.Float('Average Rating', readonly=True, group_operator='avg')
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    message_is_follower = fields.Boolean(related='ticket_id.message_is_follower')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State', readonly=True)

    def _select(self):
        return """
            SELECT DISTINCT T.id as id,
                            T.id AS ticket_id,
                            T.description,
                            T.ticket_ref AS ticket_ref,
                            T.name AS name,
                            T.create_date AS create_date,
                            T.team_id,
                            T.active AS active,
                            T.stage_id AS stage_id,
                            T.ticket_type_id,
                            T.user_id,
                            T.partner_id,
                            T.partner_name AS partner_name,
                            T.partner_email AS partner_email,
                            T.partner_phone AS partner_phone,
                            T.company_id,
                            T.kanban_state AS kanban_state,
                            T.rating_last_value AS rating_last_value,
                            AVG(rt.rating) as rating_avg,
                            T.priority AS priority,
                            T.close_hours AS ticket_close_hours,
                            T.assign_hours AS ticket_assignation_hours,
                            T.close_date AS close_date,
                            STAGE.fold AS ticket_closed,
                            SLA.stage_id as sla_stage_id,
                            SLA_S.deadline AS sla_deadline,
                            SLA.id as sla_id,
                            SLA_S.exceeded_hours AS sla_exceeded_hours,
                            SLA_S.reached_datetime >= SLA_S.deadline OR (SLA_S.reached_datetime IS NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC') AS sla_fail,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.reached_datetime >= SLA_S.deadline THEN 1
                                WHEN SLA_S.reached_datetime IS NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC' THEN 1
                                ELSE 0
                            END AS sla_status_failed,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND (SLA_S.deadline IS NULL OR SLA_S.reached_datetime < SLA_S.deadline) THEN 'reached'
                                WHEN (SLA_S.reached_datetime IS NOT NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.reached_datetime >= SLA_S.deadline) OR
                                    (SLA_S.reached_datetime IS NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC') THEN 'failed'
                                WHEN SLA_S.reached_datetime IS NULL AND (SLA_S.deadline IS NULL OR SLA_S.deadline > NOW() AT TIME ZONE 'UTC') THEN 'ongoing'
                            END AS sla_status,
                            CASE
                                WHEN (SLA_S.deadline IS NOT NULL AND SLA_S.deadline > NOW() AT TIME ZONE 'UTC') THEN TRUE ELSE FALSE
                            END AS sla_success
        """

    def _group_by(self):
        return """
                t.id,
                STAGE.fold,
                SLA.stage_id,
                SLA_S.deadline,
                SLA_S.reached_datetime,
                SLA.id,
                SLA_S.exceeded_hours
        """

    def _from(self):
        return f"""
            helpdesk_ticket T
            LEFT JOIN rating_rating rt ON rt.res_id = t.id
                    AND rt.res_model = 'helpdesk.ticket'
                    AND rt.consumed = True
                    AND rt.rating >= {RATING_LIMIT_MIN}
            LEFT JOIN helpdesk_stage STAGE ON T.stage_id = STAGE.id
            RIGHT JOIN helpdesk_sla_status SLA_S ON T.id = SLA_S.ticket_id
            LEFT JOIN helpdesk_sla SLA ON SLA.id = SLA_S.sla_id
        """

    def _where(self):
        return """
            T.active = true
        """

    def _order_by(self):
        return """
            id, sla_stage_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            WHERE %s
            GROUP BY %s
            ORDER BY %s
            )""" % (self._table, self._select(), self._from(),
                    self._where(), self._group_by(), self._order_by()))
