import json

from dateutil.relativedelta import relativedelta

from odoo import models, fields


class L10nItMonthlyTaxReportXmlExportWizard(models.TransientModel):
    _name = "l10n_it_xml_export.monthly.tax.report.xml.export.wizard"
    _description = "Italian Monthly Tax Report XML Export Wizard"

    declarant_fiscal_code = fields.Char(
        string="Declarant Fiscal Code",
        help="Codice Fiscale of the declarant.",
        default=lambda self: (self.env.company.account_representative_id or self.env.company).l10n_it_codice_fiscale,
    )
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
        ],
    )
    id_sistema = fields.Char(
        string="System ID",
        help="Unique identifier of the system that generated the file."
    )
    taxpayer_code = fields.Char(
        string="Taxpayer Fiscal Code",
        help="Codice Fiscale of the taxpayer. Defaults to the company's Codice Fiscale but can be changed.",
        default=lambda self: self.env.company.l10n_it_codice_fiscale,
    )
    parent_company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda x: x._get_default_parent_company_data()["parent_id"],
    )
    parent_company_vat_number = fields.Char(
        string="Parent VAT Number",
        help="VAT number of the parent company.",
        default=lambda x: x._get_default_parent_company_data()["vat_number"],
    )
    company_code = fields.Char(
        string="Company Code",
        help="Codice Fiscale of the company.",
        default=lambda self: "".join([char for char in self.env.company.vat if char.isdigit()]) if self.env.company.vat else False,
    )
    intermediary_code = fields.Char(
        string="Intermediary Code",
        default=lambda self: self.env.company.account_representative_id.l10n_it_codice_fiscale if self.env.company.account_representative_id else False,
    )
    submission_commitment = fields.Selection(
        string="Prepared by",
        help="If a representative is involved, this field precises whether the declaration was done by the taxpayer or the representative.",
        default="1",
        selection=[
            ("1", "the Taxpayer"),
            ("2", "the Representative"),
        ],
    )
    commitment_date = fields.Date(
        string="Date of Commitment",
        default=fields.Date.context_today,
    )
    subcontracting = fields.Boolean(string="Subcontracting", help="Check this if the company operates in sub-contracting.")
    exceptional_events = fields.Boolean(string="Exceptional Events", help="Check this if the declaration is affected by exceptional events.")
    extraordinary_operations = fields.Boolean(string="Extraordinary Operations", help="Check this if the company has undergone extraordinary operations.")
    show_method = fields.Boolean(
        string="Show Method",
        help="Check this if you want to show the method field.",
        compute="_compute_show_method",
    )
    method = fields.Selection(
        string="Method",
        help="Indicates which advance payment calculation method was used. The value of the advance payment can be found in the VP13 line of the report.",
        selection=[
            ("1", "1 - Historical Method"),
            ("2", "2 - Forecasting Method"),
            ("3", "3 - Analytical Method"),
        ],
    )

    def _get_default_parent_company_data(self):
        parent_id = self.env.company.parent_id or (hasattr(self.env.company, "company.account_tax_unit_ids") and self.env.company.account_tax_unit_ids[0].main_company_id)
        return {
            "parent_id": parent_id,
            "vat_number": "".join([char for char in parent_id.vat if char.isdigit()]) if parent_id else False,
        }

    def _compute_show_method(self):
        self.show_method = False

        submissions_periodicity = hasattr(self.env.company, "account_tax_periodicity") and self.env.company.account_tax_periodicity
        date_to = fields.Date.from_string(self.env.context['l10n_it_xml_export_monthly_tax_report_options']['date']['date_to'])
        for wizard in self:
            if submissions_periodicity == "trimester" and (date_to.month - 1) // 3 == 3:
                wizard.show_method = True
            if date_to.month == 12:
                wizard.show_method = True

    def action_generate_export(self):
        self.ensure_one()
        ctx = self._context
        report_id = ctx.get("l10n_it_xml_export_monthly_tax_report_options", {}).get("report_id")
        if report_id:
            options = self.env["account.report"].browse(report_id).get_options({})
        else:
            move = self.env['account.move'].browse(ctx["l10n_it_moves_to_post"])
            options = move._get_tax_closing_report_options(move.company_id, move.fiscal_position_id, move.tax_closing_report_id, move.date)
        options.update(ctx.get("l10n_it_xml_export_monthly_tax_report_options", {}))
        options.update(self._get_wizard_field_dict())

        if ctx.get("l10n_it_moves_to_post"):
            self.env["account.move"].browse(ctx["l10n_it_moves_to_post"]).action_post()

        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': ctx.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xml',
            }
        }

    def _get_wizard_field_dict(self):
        return {
            "declarant_fiscal_code": self.declarant_fiscal_code,
            "declarant_role_code": self.declarant_role_code,
            "id_sistema": self.id_sistema,
            "taxpayer_code": self.taxpayer_code,
            "parent_company_vat_number": self.parent_company_vat_number,
            "company_code": self.company_code,
            "intermediary_code": self.intermediary_code,
            "submission_commitment": self.submission_commitment,
            "commitment_date": fields.Date.to_string(self.commitment_date),  # Date fields are not json serializable.
            "subcontracting": self.subcontracting,
            "exceptional_events": self.exceptional_events,
            "extraordinary_operations": self.extraordinary_operations,
            "method": self.method,
        }
