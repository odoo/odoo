# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMEquipment(models.Model):
    _name = "fsm.equipment"
    _description = "Field Service Equipment"
    _inherit = ["mail.thread", "mail.activity.mixin", "fsm.model.mixin"]
    _stage_type = "equipment"

    name = fields.Char(required=True)
    person_id = fields.Many2one("fsm.person", string="Assigned Operator")
    location_id = fields.Many2one("fsm.location", string="Assigned Location")
    notes = fields.Text()
    territory_id = fields.Many2one(
        "res.territory",
        string="Territory",
        compute="_compute_territory_id",
        store=True,
        readonly=False,
    )
    branch_id = fields.Many2one(
        "res.branch",
        string="Branch",
        compute="_compute_branch_id",
        store=True,
        readonly=False,
    )
    district_id = fields.Many2one(
        "res.district",
        string="District",
        compute="_compute_district_id",
        store=True,
        readonly=False,
    )
    region_id = fields.Many2one(
        "res.region",
        string="Region",
        compute="_compute_region_id",
        store=True,
        readonly=False,
    )
    current_location_id = fields.Many2one("fsm.location", string="Current Location")
    managed_by_id = fields.Many2one("res.partner", string="Managed By")
    owned_by_id = fields.Many2one("res.partner", string="Owned By")
    parent_id = fields.Many2one("fsm.equipment", string="Parent")
    child_ids = fields.One2many("fsm.equipment", "parent_id", string="Children")
    color = fields.Integer("Color Index")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Company related to this equipment",
    )

    _sql_constraints = [
        ("name_uniq", "unique (name)", "Equipment name already exists!")
    ]

    @api.depends("location_id")
    def _compute_territory_id(self):
        for rec in self:
            rec.territory_id = rec.location_id.territory_id

    @api.depends("territory_id")
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.territory_id.branch_id

    @api.depends("branch_id")
    def _compute_district_id(self):
        for rec in self:
            rec.district_id = rec.branch_id.district_id

    @api.depends("district_id")
    def _compute_region_id(self):
        for rec in self:
            rec.region_id = rec.district_id.region_id
