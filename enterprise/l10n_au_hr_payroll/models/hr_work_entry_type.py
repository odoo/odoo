# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    l10n_au_penalty_rate = fields.Float("Penalty Rate")
    l10n_au_is_ote = fields.Boolean(string="Is OTE")
    l10n_au_work_stp_code = fields.Selection(
        selection=[
            ("G", "Gross"),
            ("T", "Overtime"),
            ("O", "Other Paid Leave"),
            ("P", "Paid Parental Leave"),
            ("W", "Workers Compensation"),
            ("A", "Ancillary and Defence Leave"),
        ],
        string="STP Code")
