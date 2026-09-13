from odoo import fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.tools import SQL


class CrmActivityReport(models.Model):
    _name = "crm.activity.report"
    _auto = False
    _description = "CRM Activity Analysis"
    _rec_name = "id"

    date = fields.Datetime("Completion Date", readonly=True)
    lead_create_date = fields.Datetime("Creation Date", readonly=True)
    date_conversion = fields.Datetime("Conversion Date", readonly=True)
    date_deadline = fields.Date("Expected Closing", readonly=True)
    date_closed = fields.Datetime("Closed Date", readonly=True)
    author_id = fields.Many2one("res.partner", "Assigned To", readonly=True)
    user_id = fields.Many2one("res.users", "Salesperson", readonly=True)
    team_id = fields.Many2one("crm.team", "Sales Team", readonly=True)
    lead_id = fields.Many2one("crm.lead", "Opportunity", readonly=True)
    body = fields.Html("Activity Description", readonly=True)
    subtype_id = fields.Many2one("mail.message.subtype", readonly=True)
    mail_activity_type_id = fields.Many2one(
        "mail.activity.type", "Activity Type", readonly=True
    )
    country_id = fields.Many2one("res.country", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    stage_id = fields.Many2one("crm.stage", readonly=True)
    partner_id = fields.Many2one("res.partner", "Customer", readonly=True)
    lead_type = fields.Selection(
        string="Type",
        selection=[("lead", "Lead"), ("opportunity", "Opportunity")],
        help="Type is used to separate Leads and Opportunities",
    )
    active = fields.Boolean(readonly=True)
    tag_ids = fields.Many2many(related="lead_id.tag_ids", readonly=True)
    won_status = fields.Selection(
        [
            ("won", "Won"),
            ("lost", "Lost"),
            ("pending", "Pending"),
        ],
        string="Is Won",
        readonly=True,
    )

    def _select(self):
        return """
            SELECT
                m.id,
                l.create_date AS lead_create_date,
                l.date_conversion,
                l.date_deadline,
                l.date_closed,
                m.subtype_id,
                m.mail_activity_type_id,
                m.author_id,
                m.date,
                m.body,
                l.id as lead_id,
                l.user_id,
                l.team_id,
                l.country_id,
                l.company_id,
                l.stage_id,
                l.partner_id,
                l.type as lead_type,
                l.active,
                l.won_status
        """

    def _from(self):
        return """
            FROM mail_message AS m
        """

    def _join(self):
        return """
            JOIN crm_lead AS l ON m.res_id = l.id
        """

    def _where(self):
        return """
            WHERE
                m.model = 'crm.lead' AND (m.mail_activity_type_id IS NOT NULL)
        """

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                "CREATE OR REPLACE VIEW %s AS (%s %s %s %s)",
                SQL.identifier(self._table),
                SQL(self._select()),
                SQL(self._from()),
                SQL(self._join()),
                SQL(self._where()),
            )
        )
