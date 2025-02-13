import json

from odoo import _, api, models, fields
from odoo.exceptions import UserError

class L10nItMonthlyTaxReportXmlExportWizard(models.TransientModel):
    _name = "l10n_it_xml_export.monthly.tax.report.xml.export.wizard"
    _description = "Italian Monthly Tax Report XML Export Wizard"

    declarant_fiscal_code = fields.Char(string="Declarant Fiscal Code", help="Codice Fiscale of the declarant.",)
    declarant_role_code = fields.Selection(
        string="Declarant Role Code",
        help="Role code of the declarant",
        default="1",
        selection=[
            ("1", "1 - Legal representative"),
            ("2", "2 - Administrator of underaged"),
            ("3", "3 - Controller of sequestered goods"),
            ("4", "4 - Fiscal representative"),
            ("5", "5 - General legatee"),
            ("6", "6 - Liquidator"),
            ("7", "7 - Extraordinary operator"),
            ("8", "8 - Bankruptcy curator"),
            ("9", "9 - Commissioned liquidator"),
            ("11", "11 - Legal guardian"),
            ("12", "12 - Sole proprietor liquidator"),
            ("13", "13 - Property manager"),
            ("14", "14 - Public representative"),
            ("15", "15 - Public liquidator"),
        ]
    )
    id_sistema = fields.Char(string="System ID", help="Unique identifier of the system that generated the file.")
    parent_vat_number = fields.Char(string="Parent VAT Number", help="VAT number of the parent company.")
    taxpayer_code = fields.Char(
        string="Taxpayer Fiscal Code",
        help="Codice Fiscale of the taxpayer. Defaults to the company's Codice Fiscale but can be changed.",
        default=lambda self: self.env.company.l10n_it_codice_fiscale
    )
    intermediary_code = fields.Char(
        string="Intermediary Code",
        default=lambda self: self.env.company.account_representative_id.l10n_it_codice_fiscale if self.env.company.account_representative_id else False
    )
    commitment_date = fields.Date(
        string="Date of Commitment",
        default=fields.Date.today()
    )
    submission_commitment = fields.Selection(
        string="Submission Commitment",
        help="If an intermediary is involved, this field precises whether the declaration was done by the taxpayer or that intermediary.",
        default="1",
        selection=[
            ("1", "Prepared by the taxpayer"),
            ("2", "Prepared by the sender"),
        ]
    )
    method = fields.Selection(
        string="Method",
        help="Indicates which advance payment calculation method was used. The value of the advance payment can be found in the VP13 line of the report.",
        selection=[
            ("1", "1 - Historical Method"),
            ("2", "2 - Forecasting Method"),
            ("3", "3 - Analytical Method"),
        ]
    )
    subcontracting = fields.Boolean(string="Subcontracting", help="Check this if the company operates in sub-contracting.")
    exceptional_events = fields.Boolean(string="Exceptional Events", help="Check this if the declaration is affected by exceptional events.")
    extraordinary_operations = fields.Boolean(string="Extraordinary Operations", help="Check this if the company has undergone extraordinary operations.")

    @api.constrains("declarant_fiscal_code")
    def _check_declarant_fiscal_code(self):
        for record in self:
            if record.declarant_fiscal_code and len(record.declarant_fiscal_code) != 16:
                raise UserError(_("Declarant tax code must be 16 characters long."))

    @api.constrains("parent_vat_number")
    def _check_parent_vat_number(self):
        for record in self:
            if record.parent_vat_number and len(record.parent_vat_number) != 11:
                raise UserError(_("Parent VAT number must be 11 characters long."))

    @api.constrains("exceptional_events")
    def _check_exceptional_events(self):
        for record in self:
            if record.exceptional_events and record.exceptional_events not in range(1, 10):
                raise UserError(_("Exceptional Events can only take a value from 1 to 9."))

    def action_generate_export(self):
        self.ensure_one()
        options = self.env.context.get("l10n_it_xml_export_monthly_tax_report_options", {})
        if not options:
            _dummy, options = self.env['account.move'].browse(self.env.context['active_id'])._get_report_options_from_tax_closing_entry()
        options.update(self._get_wizard_field_dict())
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xml',
            }
        }

    def _get_wizard_field_dict(self):
        return {
            "declarant_fiscal_code": self.declarant_fiscal_code,
            "declarant_role_code": self.declarant_role_code,
            "id_sistema": self.id_sistema,
            "parent_vat_number": self.parent_vat_number,
            "taxpayer_code": self.taxpayer_code,
            "intermediary_code": self.intermediary_code,
            "commitment_date": fields.Date.to_string(self.commitment_date),  # Date fields are not json serializable
            "submission_commitment": self.submission_commitment,
            "method": self.method,
            "subcontracting": self.subcontracting,
            "exceptional_events": self.exceptional_events,
            "extraordinary_operations": self.extraordinary_operations,
        }
