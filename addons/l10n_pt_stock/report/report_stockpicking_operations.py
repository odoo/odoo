# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportStockPickingOperation(models.AbstractModel):
    _inherit = 'report.stock.report_picking'
    _description = 'Stock picking report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.company.country_id.code == 'PT':
            self.env['stock.picking'].l10n_pt_compute_missing_hashes(self.env.company.id)
        return super()._get_report_values(docids, data=data)


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _inherit = 'report.stock.report_deliveryslip'
    _description = 'Stock delivery slip report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.company.country_id.code == 'PT':
            self.env['stock.picking'].l10n_pt_compute_missing_hashes(self.env.company.id)
        return super()._get_report_values(docids, data=data)
