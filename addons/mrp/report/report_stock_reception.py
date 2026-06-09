# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import format_date


class ReportStockReport_Reception(models.AbstractModel):
    _inherit = 'report.stock.report_reception'

    def _get_docs(self, docids):
        if self.env.context.get('default_production_ids'):
            return self.env['mrp.production'].search([('id', 'in', self.env.context.get('default_production_ids')), ('state', '!=', 'cancel')])
        return super()._get_docs(docids)

    def _get_doc_model(self):
        if self.env.context.get('default_production_ids'):
            return 'mrp.production'
        return super()._get_doc_model()

    def _get_doc_types(self):
        return super()._get_doc_types() + " or manufacturing orders"

    def _get_moves(self, docs):
        if self.env.context.get('default_production_ids'):
            return docs.move_finished_ids.filtered(lambda m: m.product_id.is_storable and m.state != 'cancel')
        return super()._get_moves(docs)

    def _get_extra_domain(self, docs):
        if self.env.context.get('default_production_ids'):
            return [('raw_material_production_id', 'not in', docs.ids)]
        return super()._get_extra_domain(docs)

    def _get_formatted_scheduled_date(self, source):
        if source._name == 'mrp.production':
            return format_date(self.env, source.date_start)
        return super()._get_formatted_scheduled_date(source)

    def _action_assign(self, in_move, out_move):
        super()._action_assign(in_move, out_move)
        parent_doc = out_move._get_source_document()
        child_doc = in_move._get_source_document()
        if parent_doc and child_doc and parent_doc._name == 'mrp.production' and child_doc._name == 'mrp.production':
            parent_doc.production_group_id.child_ids += child_doc.production_group_id
            child_doc.production_group_id.parent_ids += parent_doc.production_group_id

    def _action_unassign(self, in_move, out_move):
        super()._action_unassign(in_move, out_move)
        if in_move.production_id:
            in_move.production_id.move_dest_ids -= out_move
        parent_doc = out_move._get_source_document()
        child_doc = in_move._get_source_document()
        if parent_doc and child_doc and parent_doc._name == 'mrp.production' and child_doc._name == 'mrp.production':
            parent_doc.production_group_id.child_ids -= child_doc.production_group_id
            child_doc.production_group_id.parent_ids -= parent_doc.production_group_id
