from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    def _get_domain_crm_default_team(self):
        if not self.env.user.has_group("crm.group_use_lead"):
            return [("use_sale", "=", True), ("use_opportunities", "=", True)]
        return [("use_sale", "=", True), ("use_leads", "=", True)]

    crm_default_team_id = fields.Many2one(
        comodel_name="team.team",
        string="Default Sales Teams",
        default=lambda self: self.env["team.team"].search(
            [("use_sale", "=", True)], limit=1
        ),
        domain=lambda self: self._get_domain_crm_default_team(),
        help="Default Sales Team for new leads created through the Contact Us form.",
    )
    crm_default_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Default Salesperson",
        domain=[("share", "=", False)],
        help="Default salesperson for new leads created through the Contact Us form.",
    )
