from odoo import models, api


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _get_summable_fields(self):
        """Add to summable fields list, fields created in this module.
         - customer_rank and supplier_rank will have a better ranking for the merged partner
        """
        return super()._get_summable_fields() + ['customer_rank', 'supplier_rank']

    @api.model
    def _partner_use_in(self, aggr_ids, models):
        return self.env['account.move.line'].sudo().search(
            [('partner_id', 'in', aggr_ids),
             ('move_id.secure_sequence_number', '!=', 0)]) or super()._partner_use_in(aggr_ids=aggr_ids, models=models)
