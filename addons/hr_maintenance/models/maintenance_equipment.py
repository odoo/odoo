from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Assigned Employee",
        compute="_compute_equipment_assign",
        store=True,
        index="btree_not_null",
        readonly=False,
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Assigned Department",
        compute="_compute_equipment_assign",
        store=True,
        readonly=False,
        tracking=True,
    )
    equipment_assign_to = fields.Selection(
        selection=[
            ("department", "Department"),
            ("employee", "Employee"),
            ("other", "Other"),
        ],
        string="Used By",
        default="employee",
        required=True,
    )
    owner_user_id = fields.Many2one(
        compute="_compute_owner_user_id",
        store=True,
        readonly=False,
    )
    assign_date = fields.Date(
        compute="_compute_equipment_assign",
        store=True,
        copy=True,
        readonly=False,
    )

    @api.depends("employee_id", "department_id", "equipment_assign_to")
    def _compute_owner_user_id(self):
        for equipment in self:
            if equipment.equipment_assign_to == "employee":
                equipment.owner_user_id = equipment.employee_id.user_id
            elif equipment.equipment_assign_to == "department":
                equipment.owner_user_id = equipment.department_id.manager_id.user_id
            else:
                equipment.owner_user_id = equipment.owner_user_id or self.env.user

    @api.depends("equipment_assign_to")
    def _compute_equipment_assign(self):
        for equipment in self:
            if equipment.equipment_assign_to == "employee":
                equipment.department_id = False
                equipment.employee_id = equipment.employee_id
            elif equipment.equipment_assign_to == "department":
                equipment.employee_id = False
                equipment.department_id = equipment.department_id
            else:
                equipment.department_id = equipment.department_id
                equipment.employee_id = equipment.employee_id
            equipment.assign_date = fields.Date.context_today(self)

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        for equipment in equipments:
            partner_ids = []
            if equipment.employee_id and equipment.employee_id.user_id:
                partner_ids.append(equipment.employee_id.user_id.partner_id.id)
            if (
                equipment.department_id
                and equipment.department_id.manager_id
                and equipment.department_id.manager_id.user_id
            ):
                partner_ids.append(
                    equipment.department_id.manager_id.user_id.partner_id.id
                )
            if partner_ids:
                equipment.message_subscribe(partner_ids=partner_ids)
        return equipments

    def write(self, vals):
        partner_ids = []
        if vals.get("employee_id"):
            user_id = self.env["hr.employee"].browse(vals["employee_id"])["user_id"]
            if user_id:
                partner_ids.append(user_id.partner_id.id)
        if vals.get("department_id"):
            department = self.env["hr.department"].browse(vals["department_id"])
            if department and department.manager_id and department.manager_id.user_id:
                partner_ids.append(department.manager_id.user_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)
        return super().write(vals)

    def _track_subtype(self, init_values):
        self.check_singleton()
        if ("employee_id" in init_values and self.employee_id) or (
            "department_id" in init_values and self.department_id
        ):
            return self.env.ref("maintenance.mt_mat_assign")
        return super()._track_subtype(init_values)
