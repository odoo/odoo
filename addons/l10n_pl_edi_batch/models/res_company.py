from datetime import timedelta

from odoo import fields, models

from odoo.addons.l10n_pl_edi_batch.models.batch_download import ksef_midnight


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_batch_historic_date = fields.Datetime(
        "KSeF historic download date",
        help="The vendor bills received in KSeF before this day are still to be downloaded, down to the day KSeF "
             "became mandatory.",
        default=lambda self: ksef_midnight(fields.Date.today() - timedelta(days=1)),
    )
