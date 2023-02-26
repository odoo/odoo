from odoo import api, fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"
    _description = "Time Off Type"

    code = fields.Char('code')

