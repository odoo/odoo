# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'NO':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_no_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def _l10n_no_prepare_saft_report_values(self, report, options):
        template_vals = self._saft_prepare_report_values(report, options)

        template_vals.update({
            'xmlns': 'urn:StandardAuditFile-Taxation-Financial:NO',
            'file_version': '1.10',
            'accounting_basis': 'A',
        })
        return template_vals

    @api.model
    def l10n_no_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_vals = self._l10n_no_prepare_saft_report_values(report, options)
        file_data = self._saft_generate_file_data_with_error_check(
            report, options, template_vals, 'l10n_no_saft.saft_template_inherit_l10n_no_saft'
        )
        self.env['ir.attachment'].l10n_no_saft_validate_xml_from_attachment(file_data['file_content'])
        return file_data

    def _saft_get_account_type(self, account):
        # OVERRIDE account_saft/models/account_general_ledger
        if self.env.company.account_fiscal_country_id.code != 'NO':
            return super()._saft_get_account_type(account)
        return "GL"
