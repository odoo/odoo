# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    def action_payment_report(self, export_format='l10n_ae_wps'):
        action = super().action_payment_report()
        if self.company_id.country_code != 'AE':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
