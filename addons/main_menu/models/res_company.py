from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    show_widgets = fields.Boolean()
    announcement = fields.Char(size=140)
