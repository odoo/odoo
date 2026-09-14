from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaintenanceEquipmentCategory(models.Model):
    _name = "maintenance.equipment.category"
    _description = "Maintenance Equipment Category"

    name = fields.Char(
        string="Category Name",
        translate=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    technician_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.uid,
    )
    color = fields.Integer(string="Color Index")
    note = fields.Html(
        string="Comments",
        translate=True,
    )
    equipment_ids = fields.One2many(
        comodel_name="maintenance.equipment",
        inverse_name="category_id",
        copy=False,
    )
    equipment_count = fields.Integer(compute="_compute_equipment_count")
    maintenance_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="category_id",
        copy=False,
    )
    maintenance_count = fields.Integer(compute="_compute_maintenance_counts")
    maintenance_open_count = fields.Integer(
        string="Current Maintenance",
        compute="_compute_maintenance_counts",
    )
    fold = fields.Boolean(
        string="Folded in Maintenance Pipe",
        compute="_compute_fold",
        store=True,
    )
    equipment_properties_definition = fields.PropertiesDefinition(
        string="Equipment Properties"
    )

    @api.depends("equipment_ids.active")
    def _compute_fold(self):
        for category in self:
            category.fold = not category.equipment_ids

    def _compute_equipment_count(self):
        equipment_data = self.env["maintenance.equipment"]._read_group(
            [("category_id", "in", self.ids)], ["category_id"], ["__count"]
        )
        mapped_data = {category.id: count for category, count in equipment_data}
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)

    def _compute_maintenance_counts(self):
        Request = self.env["maintenance.request"]
        domain = [("category_id", "in", self.ids)]
        total = dict(Request._read_group(domain, ["category_id"], ["__count"]))
        open_ = dict(
            Request._read_group(
                domain + Request._get_domain_open(), ["category_id"], ["__count"]
            )
        )
        for category in self:
            category.maintenance_count = total.get(category, 0)
            category.maintenance_open_count = open_.get(category, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_maintenance_requests(self):
        if any(
            category.with_context(active_test=False).equipment_ids
            or category.maintenance_ids
            for category in self
        ):
            raise UserError(
                _(
                    "You can’t delete an equipment category if some equipment or maintenance requests are linked to it."
                )
            )
