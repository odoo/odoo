from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_simplified_invoice_limit = fields.Float(
        related='company_id.l10n_es_simplified_invoice_limit',
        readonly=False,
    )
    l10n_es_general_chart_type = fields.Selection(
        related='company_id.l10n_es_general_chart_type',
        readonly=False
    )
    l10n_es_tax_plan = fields.Selection(
        related='company_id.l10n_es_tax_plan',
        readonly=False
    )
    real_estate = fields.Boolean('Real Estate', related='company_id.real_estate')
    intracomunitary_oss = fields.Boolean('Intracomunitary, Oss', related='company_id.intracomunitary_oss')
    reagyp = fields.Boolean('REAGYP', related='company_id.reagyp')
