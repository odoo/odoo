# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

AVAILABLE_PRIORITIES = [("0", "Normal"), ("1", "Low"), ("2", "High"), ("3", "Urgent")]


class FSMStage(models.Model):
    _name = "fsm.stage"
    _description = "Field Service Stage"
    _order = "sequence, name, id"

    def _default_team_ids(self):
        default_team_id = self.env.context.get("default_team_id")
        return [default_team_id] if default_team_id else None

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    sequence = fields.Integer(default=1, help="Used to order stages. Lower is better.")
    legend_priority = fields.Text(
        "Priority Management Explanation",
        translate=True,
        help="Explanation text to help users using"
        " the star and priority mechanism on"
        " stages or orders that are in this"
        " stage.",
    )
    fold = fields.Boolean(
        "Folded in Kanban",
        help="This stage is folded in the kanban view when "
        "there are no record in that stage to display.",
    )
    is_closed = fields.Boolean(
        "Is a close stage", help="Services in this stage are considered " "as closed."
    )
    is_default = fields.Boolean("Is a default stage", help="Used a default stage")
    custom_color = fields.Char(
        "Color Code", default="#FFFFFF", help="Use Hex Code only Ex:-#FFFFFF"
    )
    description = fields.Text(translate=True)
    stage_type = fields.Selection(
        [
            ("order", "Order"),
            ("equipment", "Equipment"),
            ("location", "Location"),
            ("worker", "Worker"),
        ],
        "Type",
        required=True,
        default="order",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
    )
    team_ids = fields.Many2many(
        "fsm.team",
        "order_team_stage_rel",
        "stage_id",
        "team_id",
        string="Teams",
        default=lambda self: self._default_team_ids(),
    )

    def get_color_information(self):
        # get stage ids
        stage_ids = self.search([])
        color_information_dict = []
        for stage in stage_ids:
            color_information_dict.append(
                {
                    "color": stage.custom_color,
                    "field": "stage_id",
                    "opt": "==",
                    "value": stage.name,
                }
            )
        return color_information_dict

    @api.model_create_multi
    def create(self, vals_list):
        stages = self.search([])
        for vals in vals_list:
            for stage in stages:
                if stage.stage_type == vals.get(
                    "stage_type"
                ) and stage.sequence == vals.get("sequence"):
                    raise ValidationError(
                        _(
                            "Cannot create FSM Stage because "
                            "it has the same Type and Sequence "
                            "of an existing FSM Stage."
                        )
                    )
        return super().create(vals_list)

    @api.constrains("custom_color")
    def _check_custom_color_hex_code(self):
        if (
            self.custom_color
            and not self.custom_color.startswith("#")
            or len(self.custom_color) != 7
        ):
            raise ValidationError(_("Color code should be Hex Code. Ex:-#FFFFFF"))
