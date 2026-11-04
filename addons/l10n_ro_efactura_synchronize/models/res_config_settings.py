from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ro_edi_anaf_imported_inv_journal_id = fields.Many2one(related='company_id.l10n_ro_edi_anaf_imported_inv_journal_id', readonly=False)
