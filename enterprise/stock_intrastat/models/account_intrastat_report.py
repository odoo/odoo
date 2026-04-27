# -*- coding: utf-8 -*-

from odoo import api, models


class StockIntrastatReportCustomHandler(models.AbstractModel):
    _name = 'stock.intrastat.report.handler'
    _inherit = 'account.intrastat.report.handler'
    _description = 'Intrastat Report Custom Handler (Stock)'

    @api.model
    def _fill_missing_values(self, vals_list):
        vals_list = super()._fill_missing_values(vals_list)

        # Erase the company region code by the warehouse region code, if any
        invoice_ids = [vals['invoice_id'] for vals in vals_list]

        # If the region codes do not apply on the warehouses, no need to search for stock moves
        warehouses = self.env['stock.warehouse'].with_context(active_test=False).search([])
        regions = warehouses.mapped('intrastat_region_id')

        if not regions:
            return vals_list

        # If all moves are from the same region, assign its code to all values
        if len(regions) == 1 and all(wh.intrastat_region_id for wh in warehouses):
            for val in vals_list:
                val['region_code'] = regions.code
            return vals_list

        for invoice, vals in zip(self.env['account.move'].browse(invoice_ids), vals_list):
            stock_moves = invoice._stock_account_get_last_step_stock_moves()
            if stock_moves:
                warehouse = stock_moves[0].warehouse_id or stock_moves[0].picking_id.picking_type_id.warehouse_id
                if warehouse.intrastat_region_id.code:
                    vals['region_code'] = warehouse.intrastat_region_id.code
        return vals_list
