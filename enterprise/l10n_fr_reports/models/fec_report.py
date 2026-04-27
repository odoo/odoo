# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _
from odoo.exceptions import UserError


class FECReportCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'
    _description = 'FEC Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code != 'FR':
            return
        options.setdefault('buttons', []).append(
            {'name': _('FEC'), 'sequence': 10, 'action': 'l10n_fr_reports_open_fec_wizard'}
        )

    def l10n_fr_reports_open_fec_wizard(self, options):
        return {
            'type': 'ir.actions.act_window',
            'name': 'FEC File Generation',
            'res_model': 'l10n_fr.fec.export.wizard',
            'view_mode': 'form',
            'views': [[self.env.ref('l10n_fr_account.fec_export_wizard_view').id, 'form']],
            'target': 'new',
            'context': {**self.env.context.copy(), 'report_dates': options['date']}
        }

    def generate_fec_report(self, wizard):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options({})
        options['fec_wizard_id'] = wizard.id
        return report.export_file(options, 'generate_fec_content')

    def generate_fec_content(self, options):
        return self.env['l10n_fr.fec.export.wizard'].browse(options['fec_wizard_id']).generate_fec()


class FecExportWizard(models.TransientModel):
    _inherit = 'l10n_fr.fec.export.wizard'

    def create_fec_report_action(self):
        # OVERRIDE
        today = fields.Date.today()
        if self.date_from > today or self.date_to > today:
            raise UserError(_('You could not set the start date or the end date in the future.'))
        if self.date_from >= self.date_to:
            raise UserError(_('The start date must be inferior to the end date.'))
        return self.env['account.general.ledger.report.handler'].generate_fec_report(self)
