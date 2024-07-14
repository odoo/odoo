# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """This action will be called by the POST button on a tax report account move.
           As posting this move will generate the XML report, it won't call `action_post`
           immediately, but will open the wizard that configures this XML file.
           Validating the wizard will resume the `action_post` and take these options in
           consideration when generating the XML report.
        """
        if (self.filtered(lambda am: am.tax_closing_end_date)
                and 'BE' in self.mapped('tax_country_code')
                and 'l10n_be_reports_generation_options' not in self.env.context):
            ctx = self.env.context.copy()
            ctx['l10n_be_reports_generation_options'] = {}
            ctx['l10n_be_action_resume_post_move_ids'] = self.ids
            new_wizard = self.env['l10n_be_reports.periodic.vat.xml.export'].create({})
            view_id = self.env.ref('l10n_be_reports_post_wizard.view_account_financial_report_export').id
            return {
                'name': _('Post a tax report entry'),
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'res_model': 'l10n_be_reports.periodic.vat.xml.export',
                'type': 'ir.actions.act_window',
                'res_id': new_wizard.id,
                'target': 'new',
                'context': ctx,
            }

        return super().action_post()

    def _get_report_options_from_tax_closing_entry(self):
        """This override retrieves the generation options that were inserted in
           the context by the wizard opened by `action_post` overridden by this module,
           and merges them in the computed options.
        """
        report, options = super()._get_report_options_from_tax_closing_entry()

        l10n_be_options = self.env.context.get('l10n_be_reports_generation_options', False)
        if l10n_be_options:
            options.update(l10n_be_options)

        return report, options

    def _get_vat_report_attachments(self, report, options):
        attachments = super()._get_vat_report_attachments(report, options)

        # Add the XML along with other attachments when the VAT report is posted
        if self.env.company.account_fiscal_country_id.code == 'BE':
            xml_data = self.env[report.custom_handler_model_name].export_tax_report_to_xml(options)
            attachments.append((xml_data['file_name'], xml_data['file_content']))

        return attachments
