from odoo import api, fields, models, tools


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    def _default_employee_id(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=_default_employee_id,
    )
    owner_user_id = fields.Many2one(
        compute="_compute_owner_user_id",
        default=None,
        store=True,
        readonly=False,
    )
    equipment_id = fields.Many2one(
        domain="['|', ('employee_id', '=', employee_id), ('employee_id', '=', False)]"
    )

    @api.depends("employee_id", "equipment_id.equipment_assign_to")
    def _compute_owner_user_id(self):
        for request in self:
            if (
                request.equipment_id.equipment_assign_to == "employee"
                and request.employee_id.user_id
            ):
                request.owner_user_id = request.employee_id.user_id
            else:
                request.owner_user_id = request.owner_user_id or self.env.user

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for request in requests:
            if request.employee_id.user_id:
                request.message_subscribe(
                    partner_ids=[request.employee_id.user_id.partner_id.id]
                )
        return requests

    def write(self, vals):
        if vals.get("employee_id"):
            employee = self.env["hr.employee"].browse(vals["employee_id"])
            if employee and employee.user_id:
                self.message_subscribe(partner_ids=[employee.user_id.partner_id.id])
        return super().write(vals)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}
        email = tools.email_normalize(msg_dict.get("from"), strict=False)
        user = (
            self.env["res.users"].search([("login", "=", email)], limit=1)
            if email
            else self.env["res.users"]
        )
        if user.employee_id:
            custom_values["employee_id"] = user.employee_id.id
        return super().message_new(msg_dict, custom_values=custom_values)
