from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_nl_reports_sbr_cert_id = fields.Many2one(related='company_id.l10n_nl_reports_sbr_cert_id', readonly=False)
