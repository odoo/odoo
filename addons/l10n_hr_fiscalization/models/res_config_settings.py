from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_hr_fiscalization_mode = fields.Selection(related='company_id.l10n_hr_fiscalization_mode', readonly=False)
    l10n_hr_fiscalization_certificate = fields.Many2one(related='company_id.l10n_hr_fiscalization_certificate', readonly=False)
    l10n_hr_fiscalization_ca_intermediate_pem = fields.Binary(related='company_id.l10n_hr_fiscalization_ca_intermediate_pem', readonly=False)
    l10n_hr_fiscalization_ca_root_pem = fields.Binary(related='company_id.l10n_hr_fiscalization_ca_root_pem', readonly=False)
    l10n_hr_fiscalization_sequence_identifier = fields.Selection(related='company_id.l10n_hr_fiscalization_sequence_identifier', readonly=False)
