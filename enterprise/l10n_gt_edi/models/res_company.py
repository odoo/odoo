from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_gt_edi_vat_affiliation = fields.Selection(
        selection=[
            ("GEN", "GEN: General VAT Regime"),
            ("EXE", "EXE: Exempt Small Taxpayer Regime"),
            ("PEQ", "PEQ: Small Taxpayer Regime"),
            ("PEE", "PEE: Special Electronic Small Taxpayer"),
            ("AGR", "AGR: Agricultural Regime"),
            ("AGE", "AGE: Agro-export Regime"),
            ("ECA", "ECA: Coffee Exporter"),
            ("EXI", "EXI: VAT Exempt (Entities or institutions legally exempt from VAT)"),
        ],
        string="VAT Affiliation",
        compute="_compute_l10n_gt_edi_default_fields",
        store=True,
        readonly=False,
        help="""Selects the VAT affiliation of your company:
        GEN - General VAT Regime - Applicable to taxpayers with commercial, industrial or service activities. They must declare and pay VAT monthly, using the tax debit and credit method.
        EXE - VAT Exempt - Applies to government entities, non-profit associations and exempt activities according to the law. They do not generate or pay VAT, but must meet specific requirements before the SAT.
        PEQ - Small Taxpayer - For individuals or legal entities with annual income up to a limit established by the SAT. They pay a fixed percentage of their gross sales and file quarterly returns.
        PEE - Small Electronic Taxpayer - Similar to the Small Taxpayer regime, but adapted for electronic operations, allowing digital declarations and billing.
        AGR - Agricultural Regime - Designed for agricultural activities with specific tax benefits, allowing credits and declarations adapted to agroindustrial production.
        AGE - Electronic Agricultural Regime - Same as the agricultural regime, but for taxpayers who operate electronically, facilitating tax declaration and control processes.
        ECA - Exporter of Goods and Services - Explanation: For companies that export. It allows you to request tax credit refunds for exports and enjoy certain tax benefits.
        EXI - Exempt for Specific Income - Explanation: Applies to sectors or activities exempt from taxes according to special legislation, such as diplomatic services and certain exports of specific goods or services.
        """,
    )
    l10n_gt_edi_phrase_ids = fields.Many2many(
        related='partner_id.l10n_gt_edi_phrase_ids',
        readonly=False,
    )
    l10n_gt_edi_service_provider = fields.Selection(
        selection=[
            ("demo", "Demo"),
            ("test", "Test"),
            ("production", "Production"),
        ],
        string="Infile Web Service Provider",
        compute="_compute_l10n_gt_edi_default_fields",
        store=True,
        readonly=False,
        help="Select the demo, test, or production environment",
    )
    l10n_gt_edi_ws_prefix = fields.Char(
        string="Infile WS Username or Prefix",
        help="Username for webservices provided by Infile",
    )
    l10n_gt_edi_infile_token = fields.Char(
        string="Infile Token (LlaveFirma)",
        help="Token for Infile Webservice (provided by Infile)",
    )
    l10n_gt_edi_infile_key = fields.Char(
        string="Infile Key (LlaveAPI)",
        help="Key for Infile Webservice (provided by Infile)",
    )
    l10n_gt_edi_legal_name = fields.Char(
        string="Legal Name",
        compute="_compute_l10n_gt_edi_default_fields",
        store=True,
        readonly=False,
        help="Legal name used to fill the NombreEmisor field in the XML and 'Nombre de la Empresa' in the invoice PDF",
    )
    l10n_gt_edi_establishment_code = fields.Char(
        string="Establishment Code",
        compute="_compute_l10n_gt_edi_default_fields",
        store=True,
        readonly=False,
        help="Establishment code from the SAT configuration",
    )

    @api.onchange('parent_id')
    def _onchange_fill_l10n_gt_edi_default_fields(self):
        """
        When creating new branch guatemalan company, automatically sets some of its fields
        and trigger the compute default fields below.
        """
        if self.parent_id.country_code == 'GT':
            self.country_id = self.env.ref('base.gt')
            self.vat = self.parent_id.vat
            self.l10n_gt_edi_vat_affiliation = self.parent_id.l10n_gt_edi_vat_affiliation
            self.l10n_gt_edi_phrase_ids = self.parent_id.l10n_gt_edi_phrase_ids
            self.l10n_gt_edi_service_provider = self.parent_id.l10n_gt_edi_service_provider

    @api.depends('country_code')
    def _compute_l10n_gt_edi_default_fields(self):
        for company in self:
            if company.country_code == 'GT':
                legal_name = company.l10n_gt_edi_legal_name or company.name
                establishment_code = company.l10n_gt_edi_establishment_code or "1"

                # If the current company is a branch, use their parent's details for the legal name & establishment code.
                # We can't use `parent_ids` because it doesn't contain the parent ids yet when filling the create branch form.
                # Hence, we recursively try to get the first parent (using `parent_id`) that have a VAT.
                # If none of the parents has a VAT, it will try to get the details from the branch's root-est company.
                if parent_company := company.parent_id:
                    while parent_company and not parent_company.sudo().partner_id.vat:
                        parent_company = parent_company.parent_id

                    legal_name = parent_company.sudo().l10n_gt_edi_legal_name or parent_company.sudo().name or legal_name
                    establishment_code = parent_company.sudo().l10n_gt_edi_establishment_code or establishment_code

                company.l10n_gt_edi_vat_affiliation = company.l10n_gt_edi_vat_affiliation or "GEN"
                company.l10n_gt_edi_service_provider = company.l10n_gt_edi_service_provider or "demo"
                company.l10n_gt_edi_legal_name = legal_name
                company.l10n_gt_edi_establishment_code = establishment_code
            else:
                company.l10n_gt_edi_vat_affiliation = False
                company.l10n_gt_edi_service_provider = False
                company.l10n_gt_edi_legal_name = False
                company.l10n_gt_edi_establishment_code = False
