# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
import json


class PolishVATXMLReportExport(models.TransientModel):
    _name = "l10n_pl_reports.periodic.vat.xml.export"
    _description = "Polish Periodic VAT Report Export Wizard"

    l10n_pl_birthdate = fields.Date(
        string="Birthdate",
        help="As a natural person, the birthdate is needed",
    )
    partner_is_company = fields.Boolean(compute="_compute_partner_is_company") # used to show l10n_pl_birthdate
    l10n_pl_repayment_timeframe = fields.Selection(
        string='Repayment Timeframe',
        selection=
        [
            ('540', '15 days'),
            ('55', '25 days on VAT account'),
            ('56', '25 days on settlement account'),
            ('560', '40 days'),
            ('57', '60 days'),
            ('58', '180 days'),
        ]
    )
    l10n_pl_repayment_amount = fields.Integer("Amount to be reimbursed by the government")
    l10n_pl_repayment_future_tax = fields.Boolean("Credit the tax repayment amount towards future tax obligations")
    l10n_pl_repayment_future_tax_amount = fields.Integer("Amount to be credited towards future tax obligations")
    l10n_pl_repayment_future_tax_type = fields.Char("Type of future tax obligations to be credited")
    l10n_pl_paid_before_deadline = fields.Boolean("Tax liability has been paid in full before deadline")
    l10n_pl_is_amendment = fields.Boolean("Is an amendment")
    l10n_pl_reason_amendment = fields.Char("Reasons for the amendment")

    def _compute_partner_is_company(self):
        self.partner_is_company = self.env.company.partner_id.is_company

    def print_xml(self):
        options = self.env.context.get('l10n_pl_reports_generation_options')
        options.update({field_name: self[field_name] for field_name in self._fields if field_name[:7] == 'l10n_pl'})
        options.update({'l10n_pl_birthdate': str(self.l10n_pl_birthdate)})
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xml',
            }
        }
