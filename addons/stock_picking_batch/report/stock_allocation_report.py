from odoo import models


class StockAllocationReport(models.AbstractModel):
    _inherit = 'stock.allocation.report'

    def _get_docs(self, res_model, ids):
        if res_model == 'stock.picking.batch':
            return self.env['stock.picking.batch'].search([
                ('id', 'in', ids),
                ('picking_type_code', '!=', 'outgoing'),
                ('state', '!=', 'cancel'),
            ])
        return super()._get_docs(res_model, ids)

    def _get_docs_type(self, docs):
        if docs._name == 'stock.picking.batch':
            return self.env._("batches")
        return super()._get_docs_type(docs)

    def _get_moves(self, records):
        if records._name == 'stock.picking.batch':
            return records.move_ids.filtered(
                lambda m: m.product_id.is_storable and m.state != 'cancel'
            )
        return super()._get_moves(records)
