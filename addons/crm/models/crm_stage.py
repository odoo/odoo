from odoo import _, api, fields, models

AVAILABLE_PRIORITIES = [
    ("0", "Low"),
    ("1", "Medium"),
    ("2", "High"),
    ("3", "Very High"),
]


class CrmStage(models.Model):
    _name = "crm.stage"
    _description = "CRM Stages"
    _rec_name = "name"
    _order = "sequence, name, id"

    name = fields.Char(
        string="Stage Name",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(
        default=1,
        help="Used to order stages. Lower is better.",
    )
    is_won = fields.Boolean(string="Is Won Stage?")
    rotting_threshold_days = fields.Integer(
        string="Days to rot",
        default=0,
        help="Highlight opportunities that haven't been updated for this many days. \
        Set to 0 to disable. Changing this parameter will not affect the rotting status/date of resources last updated before this change.",
    )
    requirements = fields.Text(
        help="Enter here the internal requirements for this stage (ex: Offer sent to customer). It will appear as a tooltip over the stage's name."
    )
    team_ids = fields.Many2many(
        comodel_name="team.team",
        string="Sales Teams",
        domain=[("use_sale", "=", True)],
        ondelete="restrict",
    )
    fold = fields.Boolean(
        string="Folded in Pipeline",
        help="This stage is folded in the kanban view when there are no records in that stage to display.",
    )
    crm_team_count = fields.Integer(
        string="Sales Teams in Database",
        compute="_compute_crm_team_count",
    )
    color = fields.Integer(export_string_translation=False)

    def _compute_crm_team_count(self):
        self.crm_team_count = self.env["team.team"].search_count(
            [("use_sale", "=", True)]
        )

    @api.onchange("is_won")
    def _onchange_is_won(self):
        return {
            "warning": {
                "title": _("Do you really want to update this stage?"),
                "message": _(
                    "Changing the value of 'Is Won Stage' may induce a large number of operations, "
                    "as the probabilities of opportunities in this stage will be recomputed on saving."
                ),
            }
        }

    def write(self, vals):
        res = super().write(vals)
        if "is_won" in vals:
            won_leads = self.env["crm.lead"].search([("stage_id", "in", self.ids)])
            if won_leads and vals.get("is_won"):
                won_leads.write({"probability": 100, "automated_probability": 100})
            elif won_leads and not vals.get("is_won"):
                won_leads._compute_probabilities()
        return res
