# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportStockPickingOperation(models.AbstractModel):
    _name = 'report.stock.report_picking'
    _description = 'Stock picking report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': self.env['stock.picking'],
            'data': data,
            'docs': self.env['stock.picking'].browse(docids),
        }


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _name = 'report.stock.report_deliveryslip'
    _description = 'Stock delivery slip report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': self.env['stock.picking'],
            'data': data,
            'docs': self.env['stock.picking'].browse(docids),
        }
