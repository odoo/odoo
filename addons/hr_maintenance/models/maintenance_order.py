from odoo import api, fields, models, tools
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MaintenanceOrder(models.Model):
    _inherit = "maintenance.order"

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
        for order in self:
            if (
                order.equipment_id.equipment_assign_to == "employee"
                and order.employee_id.user_id
            ):
                order.owner_user_id = order.employee_id.user_id
            else:
                order.owner_user_id = order.owner_user_id or self.env.user

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        _debug.lifecycle("orders_created", orders=orders)
        for order in orders:
            if order.employee_id.user_id:
                order.message_subscribe(
                    partner_ids=[order.employee_id.user_id.partner_id.id]
                )
        return orders

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
        _debug.logic(
            "order_from_email", email=email or "none", employee=user.employee_id
        )
        if user.employee_id:
            custom_values["employee_id"] = user.employee_id.id
        return super().message_new(msg_dict, custom_values=custom_values)
