from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_pe_edi_stock_client_id = fields.Char(
        related="company_id.l10n_pe_edi_stock_client_id",
        readonly=False,
    )
    l10n_pe_edi_stock_client_secret = fields.Char(
        related="company_id.l10n_pe_edi_stock_client_secret",
        readonly=False,
    )
    l10n_pe_edi_stock_client_username = fields.Char(
        related="company_id.l10n_pe_edi_stock_client_username",
        readonly=False,
    )
    l10n_pe_edi_stock_client_password = fields.Char(
        related="company_id.l10n_pe_edi_stock_client_password",
        readonly=False,
    )
