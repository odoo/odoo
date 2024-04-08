from odoo import models, api


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    @api.model
    def _partner_use_in(self, aggr_ids, models):
        return self.env['pos.order'].sudo().search(
            [('partner_id', 'in', aggr_ids),
             ('l10n_fr_secure_sequence_number', '!=', 0)]) or super()._partner_use_in(aggr_ids=aggr_ids, models=models)
