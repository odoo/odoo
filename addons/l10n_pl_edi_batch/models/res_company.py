from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_batch_historic_date = fields.Datetime("KSeF historic download date")
