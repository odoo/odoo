# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ReportIntrastat(models.Model):
    _inherit = "report.intrastat"

    intrastat_id = fields.Many2one(compute='_compute_intrastat_id')

    def _compute_intrastat_id(self):
        for record in self:
            record.intrastat_id = self.env['account.invoice.line'].browse(record.id).product_id.get_intrastat_recursively()
