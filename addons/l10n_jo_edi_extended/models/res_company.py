from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jo_edi_demo_mode = fields.Boolean(string="JoFotara Demo Mode")
