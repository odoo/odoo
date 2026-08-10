from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_simplified_invoice_limit = fields.Float(
        related='company_id.l10n_es_simplified_invoice_limit',
        readonly=False,
    )

    l10n_es_tax_plan = fields.Selection(
        related='company_id.l10n_es_tax_plan',
        readonly=False
    )

    module_l10n_es_real_estates = fields.Boolean('Real Estate', readonly=False)
    igic = fields.Boolean('IGIC', related="company_id.igic", readonly=False)
    aeat = fields.Boolean('AEAT', related="company_id.aeat", readonly=False)
