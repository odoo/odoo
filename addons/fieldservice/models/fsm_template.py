# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMTemplate(models.Model):
    _name = "fsm.template"
    _description = "Field Service Order Template"

    name = fields.Char(required=True)
    instructions = fields.Text()
    category_ids = fields.Many2many("fsm.category", string="Categories")
    duration = fields.Float(help="Default duration in hours")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        index=True,
        help="Company related to this template",
    )
    type_id = fields.Many2one("fsm.order.type", string="Type")
    team_id = fields.Many2one(
        "fsm.team",
        string="Team",
        help="Choose a team to be set on orders of this template",
    )
