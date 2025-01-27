from odoo import fields, models, api

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_region_code = fields.Char(compute='_compute_l10n_pt_region_code', store=True, readonly=False)
    l10n_pt_training_mode = fields.Boolean(string="Training Mode")

    @api.depends('country_id', 'state_id')
    def _compute_l10n_pt_region_code(self):
        for company in self.filtered(lambda c: c.country_id.code == 'PT'):
            if company.state_id == self.env.ref('base.state_pt_pt-20'):
                company.l10n_pt_region_code = 'PT-AC'
            elif company.state_id == self.env.ref('base.state_pt_pt-30'):
                company.l10n_pt_region_code = 'PT-MA'
            else:
                company.l10n_pt_region_code = 'PT'

    def _get_hash_versioning_list(self):
        if self.account_fiscal_country_id.code != 'PT':
            return super()._get_hash_versioning_list()
        return list(pt_hash_utils.get_public_keys(self.env).values())

    def _verify_hashed_move(self, move, previous_hash, versioning_list, current_versioning_index):
        if self.account_fiscal_country_id.code != 'PT':
            return super()._verify_hashed_move(move, previous_hash, versioning_list, current_versioning_index)
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = pt_hash_utils.get_message_to_hash(move.date, move.l10n_pt_hashed_on, move.amount_total, move._get_l10n_pt_document_number(), previous_hash)
        return pt_hash_utils.verify_integrity(message, move.inalterable_hash, versioning_list[current_versioning_index]), current_versioning_index
