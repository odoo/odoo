from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Cashier",
        help="The employee who uses the cash register.",
    )
    cashier = fields.Char(
        string="Cashier name",
        compute="_compute_cashier",
        store=True,
    )

    @api.depends("employee_id", "user_id")
    def _compute_cashier(self):
        for order in self:
            _debug.logic(
                "pos_order_cashier",
                order=order,
                by="employee" if order.employee_id else "user",
                employee=order.employee_id,
                user=order.user_id,
            )
            if order.employee_id:
                order.cashier = order.employee_id.name
            else:
                order.cashier = order.user_id.name

    @api.model
    def _load_pos_data_fields(self, config):
        return [*super()._load_pos_data_fields(config), "employee_id"]

    def _prepare_pos_log(self, body):
        return (
            super()._prepare_pos_log(body)
            + Markup("<br/>")
            + _("Cashier %s", self.cashier)
        )
