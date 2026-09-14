from odoo import api, fields, models


class TestTeamTicket(models.Model):
    _name = "test.team.ticket"
    _inherit = ["mixin.mail.thread"]
    _description = "Team Test Ticket"

    name = fields.Char()
    kind = fields.Char()
    user_id = fields.Many2one(comodel_name="res.users")
    company_id = fields.Many2one(comodel_name="res.company")
    team_id = fields.Many2one(
        comodel_name="team.team",
        compute="_compute_team_id",
        store=True,
        readonly=False,
        domain=[("use_alpha", "=", True)],
    )

    @api.depends("user_id")
    def _compute_team_id(self):
        for ticket in self:
            ticket.team_id = self.env["team.team"]._get_default_team(
                "alpha", user_id=ticket.user_id.id
            )
