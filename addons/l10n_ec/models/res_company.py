# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ec_final_consumer_limit = fields.Monetary(
        string="EC Final Consumer Max Amount",
        default=50.0,
        help="Order total above which an Ecuadorian buyer without a RUC must provide their Cédula."
        " Set by the SRI for sales to an unidentified Consumidor Final.",
    )

    def _localization_use_documents(self):
        self.ensure_one()
        return self.chart_template == 'ec' or self.account_fiscal_country_id.code == "EC" or super()._localization_use_documents()
