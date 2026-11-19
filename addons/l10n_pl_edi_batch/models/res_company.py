from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_batch_historic_date = fields.Date(
        "KSeF historic download date",
        help="The vendor bills received in KSeF before this day are still to be downloaded, down to the day KSeF "
             "became mandatory. Set by the first download of recent bills.",
    )
