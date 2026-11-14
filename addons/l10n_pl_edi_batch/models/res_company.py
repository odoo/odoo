from datetime import timedelta

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_batch_historic_date = fields.Date(
        "KSeF historic download date",
        help="The vendor bills received in KSeF before this day are still to be downloaded, down to the day KSeF "
             "became mandatory.",
        compute='_compute_l10n_pl_edi_batch_historic_date',
        store=True,
        readonly=False,
    )

    @api.depends('l10n_pl_edi_access_token')
    def _compute_l10n_pl_edi_batch_historic_date(self):
        for company in self:
            if company.l10n_pl_edi_access_token and not company.l10n_pl_edi_batch_historic_date:
                company.l10n_pl_edi_batch_historic_date = fields.Date.today() - timedelta(days=1)
