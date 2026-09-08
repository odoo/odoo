from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_simplified_invoice_limit = fields.Float(
        related='company_id.l10n_es_simplified_invoice_limit',
        readonly=False,
    )
    l10n_es_special_vat_regime = fields.Selection(
        related='company_id.l10n_es_special_vat_regime',
        readonly=False,
    )
    module_l10n_es_edi_verifactu = fields.Boolean('Veri*Factu')
    module_l10n_es_edi_sii = fields.Boolean('SII')
    module_l10n_es_edi_tbai = fields.Boolean('TicketBai')
