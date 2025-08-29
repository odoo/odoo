# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    auto_populate_persons_on_location = fields.Boolean(
        string="Auto-populate Workers on Location based on Territory"
    )
    auto_populate_equipments_on_order = fields.Boolean(
        string="Auto-populate Equipments on Order based on Location"
    )
    search_on_complete_name = fields.Boolean(string="Search Location By Hierarchy")

    fsm_order_request_late_lowest = fields.Float(
        string="Hours of Buffer for Lowest Priority FS Orders",
        default=72,
    )
    fsm_order_request_late_low = fields.Float(
        string="Hours of Buffer for Low Priority FS Orders",
        default=48,
    )
    fsm_order_request_late_medium = fields.Float(
        string="Hours of Buffer for Medium Priority FS Orders",
        default=24,
    )
    fsm_order_request_late_high = fields.Float(
        string="Hours of Buffer for High Priority FS Orders", default=8
    )
