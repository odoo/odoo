from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _name = "maintenance.equipment"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.maintenance"]
    _description = "Maintenance Equipment"
    _check_company_auto = True

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "owner_user_id" in init_values and self.owner_user_id:
            return self.env.ref("maintenance.mt_mat_assign")
        return super()._track_subtype(init_values)

    @api.depends("serial_no")
    def _compute_display_name(self):
        for record in self:
            if record.serial_no:
                record.display_name = (record.name or "") + "/" + record.serial_no
            else:
                record.display_name = record.name

    name = fields.Char(
        string="Equipment Name",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    owner_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        index="btree_not_null",
        tracking=True,
    )
    category_id = fields.Many2one(
        comodel_name="maintenance.equipment.category",
        string="Equipment Category",
        index="btree_not_null",
        group_expand="_read_group_category_ids",
        tracking=True,
    )
    technician_user_id = fields.Many2one(
        compute="_compute_technician_user_id",
        tracking=True,
        precompute=True,
        store=True,
        readonly=False,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        check_company=True,
    )
    partner_ref = fields.Char(string="Vendor Reference")
    model = fields.Char()
    serial_no = fields.Char(
        string="Serial Number",
        copy=False,
    )
    assign_date = fields.Date(
        string="Assigned Date",
        tracking=True,
    )
    cost = fields.Float()
    note = fields.Html()
    warranty_date = fields.Date(string="Warranty Expiration Date")
    color = fields.Integer(string="Color Index")
    scrap_date = fields.Date()
    maintenance_ids = fields.One2many(
        comodel_name="maintenance.order",
        inverse_name="equipment_id",
    )
    equipment_properties = fields.Properties(
        definition="category_id.equipment_properties_definition",
        string="Properties",
        copy=True,
    )

    _serial_no = models.Constraint(
        "unique(serial_no)",
        "Another asset already exists with this serial number!",
    )

    @api.depends("category_id")
    def _compute_technician_user_id(self):
        for equipment in self:
            equipment.technician_user_id = (
                equipment.category_id.technician_user_id or equipment.technician_user_id
            )

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        equipments._add_followers()
        return equipments

    def write(self, vals):
        res = super().write(vals)
        if vals.keys() & {"owner_user_id", "technician_user_id", "category_id"}:
            self._add_followers()
        return res

    def _add_followers(self):
        for equipment in self:
            partners = (
                equipment.owner_user_id | equipment.technician_user_id
            ).partner_id
            if partners:
                equipment.message_subscribe(partner_ids=partners.ids)

    @api.model
    def _read_group_category_ids(self, categories, domain):
        """Read group customization in order to display all the categories in
        the kanban view, even if they are empty.
        """
        # bypass ir.model.access checks, but search with ir.rules
        search_domain = self.env["ir.rule"]._get_domain_accessible_records(
            categories._name
        )
        category_ids = categories.sudo()._search(search_domain, order=categories._order)
        return categories.browse(category_ids)
