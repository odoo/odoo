from odoo import fields, models
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.bus.websocket import wsrequest

_debug = DebugLog(__name__)


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _update_mail_presence(self, inactivity_period):
        super()._update_mail_presence(inactivity_period)
        if not self.env.user._is_internal():
            return
        if not self.env["res.company"]._is_presence_ip_tracking_enabled():
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
        # Written in the request's own transaction, which `retrying` commits.
        # A cursor of its own would outlive a rollback, but it also cost a
        # database connection per employee per day, raised MissingError when the
        # employee was not visible to it, and put this whole branch beyond the
        # reach of a TransactionCase -- which is why it had no tests. Losing a
        # stamp to a rollback costs nothing: the guard above is the date itself,
        # so the next heartbeat records it again.
        employee.hr_presence_ip_date = today
        employee.hr_presence_state_display = employee.hr_presence_state
        _debug.lifecycle("presence_ip_recorded", employee=employee, day=today)
