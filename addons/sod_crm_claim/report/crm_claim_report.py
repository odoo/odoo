# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import fields, models, tools

AVAILABLE_PRIORITIES = [("0", "Low"), ("1", "Normal"), ("2", "High")]


class crm_claim_report(models.Model):
    """CRM Claim Report"""

    _name = "crm.claim.report"
    _auto = False
    _description = "CRM Claim Report"

    user_id = fields.Many2one("res.users", string="User", readonly=True)
    team_id = fields.Many2one("crm.team", string="Team", readonly=True)
    nbr = fields.Integer(string="# of Returns", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    create_date = fields.Datetime(readonly=True, index=True)
    claim_date = fields.Datetime(string="Return Date", readonly=True)
    delay_close = fields.Float(
        string="Delay to close",
        digits=(16, 2),
        readonly=True,
        group_operator="avg",
        help="Number of Days to close the case",
    )
    stage_id = fields.Many2one(
        "crm.claim.stage",
        string="Stage",
        readonly=True,
        domain="[('team_ids','=',team_id)]",
    )
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True)
    priority = fields.Selection(AVAILABLE_PRIORITIES)
    date_closed = fields.Datetime("Close Date", readonly=True, index=True)
    date_deadline = fields.Date("Deadline", readonly=True, index=True)
    delay_expected = fields.Float(
        "Overpassed Deadline", digits=(16, 2), readonly=True, group_operator="avg"
    )
    email = fields.Integer("# Emails", readonly=True)
    subject = fields.Char("Return Subject", readonly=True)

    def init(self):
        """Display Number of cases And Team Name
        @param cr: the current row, from the database cursor,
        """
        cr = self.env.cr
        tools.drop_view_if_exists(cr, "crm_claim_report")
        cr.execute(
            """
create or replace view crm_claim_report as (
    select
        min(c.id) as id,
        c.date as claim_date,
        c.date_closed as date_closed,
        c.date_deadline as date_deadline,
        c.user_id,
        c.stage_id,
        c.team_id,
        c.partner_id,
        c.company_id,
        c.name as subject,
        count(*) as nbr,
        c.priority as priority,
        c.create_date as create_date,
        avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close,
        (SELECT count(id) FROM mail_message WHERE model='crm.claim' AND res_id=c.id) AS email,
        extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24) as  delay_expected
    from
        crm_claim c
    group by c.date,\
            c.user_id,c.team_id, c.stage_id,\
            c.partner_id,c.company_id,c.create_date,
            c.priority,c.date_deadline,c.date_closed,c.id
            )"""
        )
