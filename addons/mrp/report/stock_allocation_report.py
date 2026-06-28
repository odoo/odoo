from odoo import models


class StockAllocationReport(models.AbstractModel):
    _inherit = 'stock.allocation.report'

    def _get_docs(self, res_model, ids):
        if res_model == 'mrp.production':
            return self.env['mrp.production'].search([
                ('id', 'in', ids),
                ('state', '!=', 'cancel'),
            ])
        return super()._get_docs(res_model, ids)

    def _get_docs_type(self, docs):
        if docs._name == 'mrp.production':
            return self.env._("manufacturing orders")
        return super()._get_docs_type(docs)

    def _get_moves(self, records):
        if records._name == 'mrp.production':
            return records.move_finished_ids.filtered(
                lambda m: m.product_id.is_storable and m.state != 'cancel'
            )
        return super()._get_moves(records)
