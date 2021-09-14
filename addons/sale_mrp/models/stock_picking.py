# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _log_activity_get_documents(self, orig_obj_changes, stream_field, stream, sorted_method=False, groupby_method=False):
        documents = super()._log_activity_get_documents(orig_obj_changes, stream_field, stream, sorted_method, groupby_method)

        # Filter out documents directly related to a SO.
        if stream == 'DOWN' and stream_field == 'move_dest_ids':
            filtered_docs = {}
            for (parent, responsible), rcontext in documents.items():
                # Parent can something else than stock_picking. Have to check that sale_id actually exists on that recordset
                if 'sale_id' not in parent._fields or not parent.sale_id:
                    filtered_docs[(parent, responsible)] = rcontext
            documents = filtered_docs
        return documents
