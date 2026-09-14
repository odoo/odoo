from odoo import fields, models
from odoo.api import Environment
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry

from odoo.addons.bus.websocket import wsrequest

_debug = DebugLog(__name__)


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _update_mail_presence(self, inactivity_period):
        super()._update_mail_presence(inactivity_period)
        if not self.env.user._is_internal():
            return
        if not self.env["res.company"]._hr_presence_any_ip_control():
            return
        employee = (
            self.env["hr.employee"]
            .sudo()
            .search([("user_id", "=", self.env.user.id)], limit=1)
        )
        company = employee.company_id
        if not company.hr_presence_control_ip:
            return
        req = request or wsrequest
        ip_address = req.httprequest.remote_addr
        if ip_address not in company._hr_presence_valid_ips():
            _debug.logic("presence_ip_rejected", employee=employee, ip=ip_address)
            return
        today = fields.Datetime.context_timestamp(
            employee.with_context(tz=employee.tz or "UTC"), fields.Datetime.now()
        ).date()
        if employee.hr_presence_ip_date == today:
            return
        # A cursor of its own: the evidence must outlive a websocket
        # transaction that rolls back for unrelated reasons.
        with Registry(self.env.cr.dbname).cursor() as cr:
            env = Environment(cr, self.env.user.id, {})
            env["hr.employee"].browse(employee.id).sudo().hr_presence_ip_date = today
        employee.invalidate_recordset(["hr_presence_ip_date"])
        _debug.lifecycle("presence_ip_recorded", employee=employee, day=today)
