from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    gst_registered = fields.Boolean(string="GST registered", help="Enable if your company is registered for GST.")
