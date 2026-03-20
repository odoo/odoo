from odoo import api, fields, models


class AccountResequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'

    # Technical field to display (or not) banner in wizard
    l10n_es_edi_verifactu_required_in_prod = fields.Boolean(compute='_compute_l10n_es_edi_verifactu_required_in_prod')

    @api.depends('move_ids.country_code', 'move_ids.l10n_es_edi_verifactu_required', 'move_ids.company_id.l10n_es_edi_verifactu_test_environment')
    def _compute_l10n_es_edi_verifactu_required_in_prod(self):
        for wizard in self:
            wizard.l10n_es_edi_verifactu_required_in_prod = (
                any(move.country_code == 'ES' and move.l10n_es_edi_verifactu_required for move in wizard.move_ids)
                and any(not company.l10n_es_edi_verifactu_test_environment for company in wizard.move_ids.company_id)
            )
