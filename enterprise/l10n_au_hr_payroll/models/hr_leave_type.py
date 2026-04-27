# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    l10n_au_leave_type = fields.Selection(
        selection=[
            ("annual", "General Leave"),
            ("long_service", "Long Service"),
            ("personal", "Unpaid at Termination"),
        ],
        default="personal",
        required=True,
        string="Unused Leave Type"
    )
