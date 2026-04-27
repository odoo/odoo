# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountTaxReportActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('tax_report', 'Tax report')])

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['account_reports.tax_closing_activity_type'] = {
            'res_model': 'account.journal',
            'unlink': False,
        }
        info['account_reports.mail_activity_type_tax_report_to_pay'] = {
            'res_model': 'account.move',
            'unlink': False,
        }
        info['account_reports.mail_activity_type_tax_report_to_be_sent'] = {
            'res_model': 'account.move',
            'unlink': False,
        }
        return info
