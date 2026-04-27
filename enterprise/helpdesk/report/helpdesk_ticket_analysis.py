# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY
from odoo.addons.rating.models.rating_data import RATING_LIMIT_MIN


class HelpdeskTicketReport(models.Model):
    _name = 'helpdesk.ticket.report.analysis'
    _description = "Ticket Analysis"
    _auto = False
    _order = 'create_date DESC'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', readonly=True)
    description = fields.Text(readonly=True)
    tag_ids = fields.Many2many('helpdesk.tag', relation='helpdesk_tag_helpdesk_ticket_rel',
        column1='helpdesk_ticket_id', column2='helpdesk_tag_id',
        string='Tags', readonly=True)
    ticket_ref = fields.Char(string='Ticket IDs Sequence', readonly=True)
    name = fields.Char(string='Subject', readonly=True)
    sla_fail = fields.Boolean(related="ticket_id.sla_fail", readonly=True)
    sla_success = fields.Boolean("SLA Status Success", aggregator='bool_or', readonly=True)
    sla_ids = fields.Many2many('helpdesk.sla', 'helpdesk_sla_status', 'ticket_id', 'sla_id', string="SLAs", copy=False)
    sla_status_ids = fields.One2many('helpdesk.sla.status', 'ticket_id', string="SLA Status")
    create_date = fields.Datetime("Ticket Creation Date", readonly=True)
    priority = fields.Selection(TICKET_PRIORITY, string='Minimum Priority', readonly=True)
    user_id = fields.Many2one('res.users', string="Assigned To", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    partner_name = fields.Char(string='Customer Name', readonly=True)
    partner_email = fields.Char(string='Customer Email', readonly=True)
    partner_phone = fields.Char(string='Customer Phone', readonly=True)
    stage_id = fields.Many2one('helpdesk.stage', string="Stage", readonly=True)
    sla_deadline = fields.Datetime("Ticket Deadline", readonly=True)
    ticket_deadline_hours = fields.Float("Working Hours until SLA Deadline", aggregator="avg", readonly=True)
    ticket_close_hours = fields.Float("Working Hours to Close", aggregator="avg", readonly=True)
    ticket_open_hours = fields.Float("Hours Open", aggregator="avg", readonly=True)
    ticket_assignation_hours = fields.Float("Working Hours to Assign", aggregator="avg", readonly=True)
    close_date = fields.Datetime("Closing Date", readonly=True)
    assign_date = fields.Datetime("First assignment date", readonly=True)
    rating_last_value = fields.Float("Rating (1-5)", aggregator="avg", readonly=True)
    active = fields.Boolean("Active", readonly=True)
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    message_is_follower = fields.Boolean(related='ticket_id.message_is_follower', export_string_translation=False)
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State', readonly=True)
    first_response_hours = fields.Float("Hours to First Response", aggregator="avg", readonly=True)
    avg_response_hours = fields.Float("Average Hours to Respond", aggregator="avg", readonly=True)
    rating_avg = fields.Float('Average Rating', readonly=True, aggregator='avg')

    def _select(self):
        select_str = """
            SELECT T.id AS id,
                   T.id AS ticket_id,
                   T.description,
                   T.ticket_ref AS ticket_ref,
                   T.name AS name,
                   T.create_date AS create_date,
                   T.priority AS priority,
                   T.user_id AS user_id,
                   T.partner_id AS partner_id,
                   T.partner_name AS partner_name,
                   T.partner_email AS partner_email,
                   T.partner_phone AS partner_phone,
                   T.stage_id AS stage_id,
                   T.sla_deadline AS sla_deadline,
                   NULLIF(T.sla_deadline_hours, 0) AS ticket_deadline_hours,
                   NULLIF(T.close_hours, 0) AS ticket_close_hours,
                   CASE
                     WHEN EXTRACT(EPOCH FROM (COALESCE(T.close_date, NOW() AT TIME ZONE 'UTC') - T.create_date)) / 3600 < 1 THEN NULL
                     ELSE EXTRACT(EPOCH FROM (COALESCE(T.close_date, NOW() AT TIME ZONE 'UTC') - T.create_date)) / 3600
                   END AS ticket_open_hours,
                   NULLIF(T.assign_hours, 0) AS ticket_assignation_hours,
                   T.close_date AS close_date,
                   T.assign_date AS assign_date,
                   CASE WHEN ht.use_rating AND COUNT(rt.id) > 0 THEN T.rating_last_value ELSE NULL END as rating_last_value,
                   CASE WHEN ht.use_rating AND COUNT(rt.id) > 0 THEN AVG(rt.rating) ELSE NULL END as rating_avg,
                   T.active AS active,
                   T.team_id AS team_id,
                   T.company_id AS company_id,
                   T.kanban_state AS kanban_state,
                   NULLIF(T.first_response_hours, 0) AS first_response_hours,
                   NULLIF(T.avg_response_hours, 0) AS avg_response_hours,
                   CASE
                       WHEN (T.sla_deadline IS NOT NULL AND T.sla_deadline > NOW() AT TIME ZONE 'UTC') THEN TRUE ELSE FALSE
                   END AS sla_success
        """
        return select_str

    def _group_by(self):
        return """
                t.id,
                ht.use_rating
        """

    def _from(self):
        from_str = f"""
            helpdesk_ticket T
                LEFT JOIN rating_rating rt ON rt.res_id = t.id
                        AND rt.res_model = 'helpdesk.ticket'
                        AND rt.consumed = True
                        AND rt.rating >= {RATING_LIMIT_MIN}
                INNER JOIN helpdesk_team ht ON ht.id = t.team_id
        """
        return from_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            GROUP BY %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))
