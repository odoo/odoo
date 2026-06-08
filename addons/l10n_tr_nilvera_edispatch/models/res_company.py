from dateutil.relativedelta import relativedelta

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tr_edespatch_purchase_last_fetched_date = fields.Datetime(default=lambda s: fields.Datetime.now() - relativedelta(months=1))
