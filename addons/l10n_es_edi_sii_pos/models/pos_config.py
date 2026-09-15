from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_es_sii_required = fields.Boolean(
        string="SII Required",
        related="company_id.l10n_es_sii_required"
    )
