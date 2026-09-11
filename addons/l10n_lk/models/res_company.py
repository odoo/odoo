# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_lk_vat_registered = fields.Boolean(
        string="Sri Lanka: VAT Registered",
        help="Indicates if this company is registered for VAT in Sri Lanka. "
        "This defaults invoice printout to this partner to tax invoice for taxable supplies.",
        related="partner_id.l10n_lk_vat_registered",
        readonly=False,
    )
