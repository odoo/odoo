# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    l10n_sa_wps_file_reference = fields.Char(string="WPS File Reference", copy=False)

    _sql_constraints = [
        ('l10n_sa_wps_unique_reference', 'UNIQUE(l10n_sa_wps_file_reference)',
         'WPS File reference must be unique'),
    ]

    def _l10n_sa_wps_generate_file_reference(self):
        self.ensure_one()
        if not self.l10n_sa_wps_file_reference:
            # Required unique 16 character reference
            self.l10n_sa_wps_file_reference = self.env['ir.sequence'].next_by_code("l10n_sa.wps")
            self.slip_ids.l10n_sa_wps_file_reference = self.l10n_sa_wps_file_reference
        return self.l10n_sa_wps_file_reference

    def action_payment_report(self, export_format='l10n_sa_wps'):
        action = super().action_payment_report()
        if self.company_id.country_code != 'SA':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
