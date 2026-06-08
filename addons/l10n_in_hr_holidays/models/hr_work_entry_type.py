# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    l10n_in_is_sandwich_leave = fields.Boolean(
        help="""If a leave is covering holidays, the holiday period will be included in the requested time.
        The time took in addition will have the same treatment (allocation, pay, reports) as the initial request.
        Holidays includes public holidays, national days, paid holidays and week-ends.""")
    l10n_in_sandwich_policy = fields.Selection(
        selection=[
            ("full", "Full Sandwich Policy"),
            ("weekend", "Weekend-Only Policy"),
            ("public_holiday", "Public Holiday-Only Policy"),
        ],
        string="Sandwich Leave Policy",
        default="full",
        help="""Full Sandwich Policy – Count both weekends and public holidays between two leave days.
        Weekend-Only Policy – Apply only if weekends fall between leave days.
        Public Holiday-Only Policy – Apply only if public holidays fall between leave days.""")
    l10n_in_is_limited_to_optional_days = fields.Boolean(
        help="""Enable this option to restrict Flexi Leave to specific days, ensuring that only days marked as
        Optional Holidays can be selected. This helps validate that employees can only choose days from the designated
        Optional Holiday list for their Flexi Leave.""")
