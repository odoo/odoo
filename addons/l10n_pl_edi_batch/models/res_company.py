from datetime import timedelta

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_batch_historic_date = fields.Datetime(
        "KSeF historic download date",
        default=lambda self: fields.Datetime.start_of(fields.Datetime.now(), 'day') - timedelta(days=1),
    )
