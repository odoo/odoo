# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    l10n_ec_final_consumer_limit = fields.Float(
        string="EC Final Consumer Max Amount",
        default=50.0,
        help="Order total, in company currency, above which an Ecuadorian buyer without a RUC must"
        " provide their Cédula. Set by the SRI for sales to an unidentified Consumidor Final.",
    )
