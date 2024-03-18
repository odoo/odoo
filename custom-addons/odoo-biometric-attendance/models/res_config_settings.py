# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    entry_strategy = fields.Selection(
        [
            ("1", "First Record as Check-In, Last as Check-Out"),
            ("2", "Use Recorded Times for Check-In/Out"),
            ("3", "Alternate Records as Check-In/Out Starting with Check-In"),
        ],
        string="Attendance Entry Strategy",
        default="2",
        help="Determines how the attendance records are interpreted. "
        "Option 1 treats the first record of the day as check-in and the "
        "last as check-out. Option 2 uses the actual times recorded by the "
        "device. Option 3 alternates between check-in and check-out for each "
        "record, starting with check-in.",
    )
    update_device = fields.Boolean("Update Device Automatically", default=False)
    device_api_base_url = fields.Char(
        "Device API Base URL",
        default="http://robot.camsunit.com/external/1.0/user",
        help="Base URL of the device API.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        get_param = self.env["ir.config_parameter"].sudo().get_param
        res.update(
            entry_strategy=get_param(
                "odoo-biometric-attendance.entry_strategy", default="1"
            ),
            update_device=get_param(
                "odoo-biometric-attendance.update_device", default=False
            ),
            device_api_base_url=get_param(
                "odoo-biometric-attendance.device_api_base_url",
                default="http://robot.camsunit.com/external/1.0/user",
            ),
        )
        return res

    @api.model
    def set_values(self):
        set_param = self.env["ir.config_parameter"].sudo().set_param
        set_param("odoo-biometric-attendance.entry_strategy", self.entry_strategy)
        set_param("odoo-biometric-attendance.update_device", self.update_device)
        set_param(
            "odoo-biometric-attendance.device_api_base_url", self.device_api_base_url
        )
        return super().set_values()
