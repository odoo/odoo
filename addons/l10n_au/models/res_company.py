from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_au_is_gst_registered = fields.Boolean(string="Australia GST registered", help="Enable if your company is registered for GST.")
