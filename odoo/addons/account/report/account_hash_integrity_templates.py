# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReportAccountHashIntegrity(models.AbstractModel):
    _name = 'report.account.report_hash_integrity'
    _description = 'Get hash integrity result as PDF.'

    @api.model
    def _get_report_values(self, docids, data=None):
        if data:
            data.update(self.env.company._check_hash_integrity())
        else:
            data = self.env.company._check_hash_integrity()
        return {
            'doc_ids' : docids,
            'doc_model' : self.env['res.company'],
            'data' : data,
            'docs' : self.env['res.company'].browse(self.env.company.id),
        }
