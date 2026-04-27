# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PrintBatchPayment(models.AbstractModel):
    _name = 'report.account_batch_payment.print_batch_payment'
    _template = 'account_batch_payment.print_batch_payment'
    _description = 'Batch Deposit Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_name = 'account_batch_payment.print_batch_payment'
        report = self.env['ir.actions.report']._get_report_from_name(report_name)
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
        }
