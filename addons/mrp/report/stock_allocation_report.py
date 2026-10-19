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

    def _allocate_moves(self, in_move, out_move):
        res = super()._allocate_moves(in_move, out_move)
        parent_doc = out_move._get_source_document()
        child_doc = in_move._get_source_document()
        if parent_doc and child_doc and parent_doc._name == 'mrp.production' and child_doc._name == 'mrp.production':
            parent_doc.production_group_id.child_ids += child_doc.production_group_id
            child_doc.production_group_id.parent_ids += parent_doc.production_group_id
        return res

    def _unallocate_moves(self, in_move, out_move):
        res = super()._unallocate_moves(in_move, out_move)
        if in_move.production_id:
            in_move.production_id.move_dest_ids -= out_move
        parent_doc = out_move._get_source_document()
        child_doc = in_move._get_source_document()
        if parent_doc and child_doc and parent_doc._name == 'mrp.production' and child_doc._name == 'mrp.production':
            parent_doc.production_group_id.child_ids -= child_doc.production_group_id
            child_doc.production_group_id.parent_ids -= parent_doc.production_group_id
        return res
