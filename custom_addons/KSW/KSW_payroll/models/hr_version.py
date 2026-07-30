from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    mobile_allowance = fields.Monetary(
        string="Mobile Allowance",
        help="Mobile allowance",
    )

