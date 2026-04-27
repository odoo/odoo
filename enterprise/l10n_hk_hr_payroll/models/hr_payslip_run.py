# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    l10n_hk_autopay = fields.Boolean(related='company_id.l10n_hk_autopay')
    l10n_hk_autopay_export_first_batch = fields.Binary(string="HSBC Autopay File", help="Exported HSBC Autopay .apc file")
    l10n_hk_autopay_export_first_batch_date = fields.Datetime(string="HSBC Generation Date", help="Creation date of the payment file")
    l10n_hk_autopay_export_first_batch_filename = fields.Char(string="File Name - First Batch", help="Exported HSBC Autopay .apc file name")
    l10n_hk_autopay_export_second_batch = fields.Binary(string="HSBC Autopay File - Second Batch", help="Exported HSBC Autopay .apc file")
    l10n_hk_autopay_export_second_batch_date = fields.Datetime(string="HSBC Generation Date - Second Batch", help="Creation date of the payment file")
    l10n_hk_autopay_export_second_batch_filename = fields.Char(string="File Name - Second Batch", help="Exported HSBC Autopay .apc file name")

    def action_open_hsbc_autopay_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate HSBC Autopay Report.'),
            'res_model': 'hr.payslip.run.hsbc.autopay.wizard',
            'view_mode': 'form',
            'view_id': 'hr_payslip_run_hsbc_autopay_view_form',
            'views': [(False, 'form')],
            'target': 'new',
        }
