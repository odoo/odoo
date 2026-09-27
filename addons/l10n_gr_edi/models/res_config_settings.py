from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_gr_edi_aade_id = fields.Char(related='company_id.l10n_gr_edi_aade_id', readonly=False)
    l10n_gr_edi_aade_key = fields.Char(related='company_id.l10n_gr_edi_aade_key', readonly=False)
    l10n_gr_edi_branch_number = fields.Integer(related='company_id.l10n_gr_edi_branch_number', readonly=False)
    l10n_gr_edi_test_env = fields.Boolean(related='company_id.l10n_gr_edi_test_env', readonly=False)
