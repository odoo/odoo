from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tr_tax_office_id = fields.Many2one(
        related='partner_id.l10n_tr_tax_office_id',
        readonly=False,
        help="Specifies the official Turkish Tax Office where this partner is registered. "
        "This is required for generating valid e-Invoices for this partner.",
    )
