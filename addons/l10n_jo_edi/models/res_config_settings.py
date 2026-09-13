from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_jo_edi_sequence_income_source = fields.Char(
        related="company_id.l10n_jo_edi_sequence_income_source",
        string="JoFotara Sequence of Income Source",
        readonly=False,
    )
    l10n_jo_edi_secret_key = fields.Char(
        related="company_id.l10n_jo_edi_secret_key",
        string="JoFotara Secret Key",
        readonly=False,
    )
    l10n_jo_edi_client_identifier = fields.Char(
        related="company_id.l10n_jo_edi_client_identifier",
        string="JoFotara Client ID",
        readonly=False,
    )
    l10n_jo_edi_taxpayer_type = fields.Selection(
        related="company_id.l10n_jo_edi_taxpayer_type",
        string="JoFotara Taxpayer Type",
        readonly=False,
    )
    l10n_jo_edi_demo_mode = fields.Boolean(
        related="company_id.l10n_jo_edi_demo_mode",
        string="JoFotara Demo Mode",
        readonly=False,
    )
