from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_jo_edi_client_id = fields.Char(string="Client ID", related="company_id.l10n_jo_edi_client_id", readonly=False)
    l10n_jo_edi_secret_key = fields.Char(string="Secret Key", related="company_id.l10n_jo_edi_secret_key", readonly=False)
    l10n_jo_edi_sequence_income_source = fields.Char(string="Sequence of Income Source", related="company_id.l10n_jo_edi_sequence_income_source", readonly=False)
    l10n_jo_edi_taxpayer_type = fields.Selection(string="Taxpayer type", related="company_id.l10n_jo_edi_taxpayer_type", readonly=False)
