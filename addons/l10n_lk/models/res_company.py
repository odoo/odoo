# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_lk_vat_registered = fields.Boolean(
        string="VAT Registered?",
        help="Indicates if this company is registered for VAT in Sri Lanka. "
        "Tax invoices can only be issued when both supplier and buyer are VAT registered.",
        related="partner_id.l10n_lk_vat_registered",
        readonly=False,
    )
