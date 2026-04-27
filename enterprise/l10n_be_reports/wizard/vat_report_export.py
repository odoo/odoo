# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields
import json
import base64


class AccountFinancialReportXMLReportExport(models.TransientModel):
    _name = "l10n_be_reports.periodic.vat.xml.export"
    _description = "Belgian Periodic VAT Report Export Wizard"

    ask_restitution = fields.Boolean()
    client_nihil = fields.Boolean()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    calling_export_wizard_id = fields.Many2one(string="Calling Export Wizard", comodel_name="account_reports.export.wizard", help="Optional field containing the report export wizard calling this wizard, if there is one.")
    comment = fields.Text()

    def _l10n_be_reports_vat_export_generate_options(self):
        return {
            'ask_restitution': self.ask_restitution,
            'client_nihil': self.client_nihil,
            'comment': self.comment,
        }

    def print_xml(self):
        if self.calling_export_wizard_id and not self.calling_export_wizard_id.l10n_be_reports_periodic_vat_wizard_id:
            self.calling_export_wizard_id.l10n_be_reports_periodic_vat_wizard_id = self
            return self.calling_export_wizard_id.export_report()
        else:
            options = self.env.context.get('l10n_be_reports_generation_options')
            options.update(self._l10n_be_reports_vat_export_generate_options())
            return {
                'type': 'ir_actions_account_report_download',
                'data': {
                    'model': self.env.context.get('model'),
                    'options': json.dumps(options),
                    'file_generator': 'export_tax_report_to_xml',
                }
            }
