# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMTag(models.Model):
    _name = "fsm.tag"
    _description = "Field Service Tag"

    name = fields.Char(required=True)
    parent_id = fields.Many2one("fsm.tag", string="Parent")
    color = fields.Integer("Color Index", default=10)
    full_name = fields.Char(compute="_compute_full_name")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.user.company_id,
        help="Company related to this tag",
    )

    _sql_constraints = [("name_uniq", "unique (name)", "Tag name already exists!")]

    def _compute_full_name(self):
        for record in self:
            record.full_name = (
                record.parent_id.name + "/" + record.name
                if record.parent_id
                else record.name
            )
