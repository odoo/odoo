# © 2022 Florian Kantelberg - initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    dark_mode = fields.Boolean()
    dark_mode_device_dependent = fields.Boolean("Device Dependent Dark Mode")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "dark_mode_device_dependent",
            "dark_mode",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "dark_mode_device_dependent",
            "dark_mode",
        ]
