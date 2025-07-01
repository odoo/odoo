# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrWebsocket(models.AbstractModel):
    """Override to handle hr_employee specific features (presence in particular)."""

    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        new_channels_list = []
        employee_channel_ids = []
        has_employee_public_access = self.env["hr.employee.public"].has_access("read")

        for channel in list(channels):
            if not isinstance(channel, str) or not channel.startswith("hr.employee_"):
                new_channels_list.append(channel)
                continue
            emp_id = channel[len("hr.employee_"):]
            if emp_id.isdigit() and has_employee_public_access:
                employee_channel_ids.append(int(emp_id))

        if employee_channel_ids and has_employee_public_access:
            new_channels_list.extend(self.env["hr.employee.public"].browse(employee_channel_ids).exists().employee_id)
        return super()._build_bus_channel_list(new_channels_list)
