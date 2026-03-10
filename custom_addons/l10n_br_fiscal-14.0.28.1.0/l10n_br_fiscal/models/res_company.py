# Copyright (C) 2013  Renato Lima - Akretion
# Copyright (C) 2020  Luis Felipe Mileo - KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import api, fields, models

from ..constants.fiscal import (
    COEFFICIENT_R,
    INDUSTRY_TYPE,
    INDUSTRY_TYPE_TRANSFORMATION,
    PROCESSADOR,
    PROCESSADOR_NENHUM,
    PROFIT_CALCULATION,
    PROFIT_CALCULATION_PRESUMED,
    TAX_DOMAIN_CBS,
    TAX_DOMAIN_COFINS,
    TAX_DOMAIN_COFINS_WH,
    TAX_DOMAIN_CSLL,
    TAX_DOMAIN_CSLL_WH,
    TAX_DOMAIN_IBS,
    TAX_DOMAIN_ICMS,
    TAX_DOMAIN_ICMS_SN,
    TAX_DOMAIN_INSS,
    TAX_DOMAIN_INSS_WH,
    TAX_DOMAIN_IPI,
    TAX_DOMAIN_IRPJ,
    TAX_DOMAIN_IRPJ_WH,
    TAX_DOMAIN_ISSQN,
    TAX_DOMAIN_ISSQN_WH,
    TAX_DOMAIN_PIS,
    TAX_DOMAIN_PIS_WH,
    TAX_FRAMEWORK,
    TAX_FRAMEWORK_NORMAL,
    TAX_FRAMEWORK_SIMPLES,
    TAX_FRAMEWORK_SIMPLES_ALL,
)

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_company_address_field_names(self):
        partner_fields = super()._get_company_address_field_names()
        return partner_fields + [
            "tax_framework",
            "legal_nature_id",
            "cnae_main_id",
        ]

    def _inverse_legal_nature_id(self):
        """Write the l10n_br specific functional fields."""
        for c in self:
            c.partner_id.legal_nature_id = c.legal_nature_id

    def _inverse_cnae_main_id(self):
        """Write the l10n_br specific functional fields."""
        for c in self:
            c.partner_id.cnae_main_id = c.cnae_main_id

    def _inverse_tax_framework(self):
        """Write the l10n_br specific functional fields."""
        for c in self:
            c.partner_id.tax_framework = c.tax_framework

    @api.depends("cnae_main_id", "annual_revenue", "payroll_amount")
    def _compute_simplified_tax(self):
        for record in self:
            record.coefficient_r = False
            if record.payroll_amount and record.annual_revenue:
                coefficient_r_percent = record.payroll_amount / record.annual_revenue
                if coefficient_r_percent > COEFFICIENT_R:
                    record.coefficient_r = True
                record.coefficient_r_percent = coefficient_r_percent

            simplified_tax_id = self.env["l10n_br_fiscal.simplified.tax"].search(
                [
                    ("cnae_ids", "=", record.cnae_main_id.id),
                    ("coefficient_r", "=", record.coefficient_r),
                ]
            )
            record.simplified_tax_id = simplified_tax_id

            if simplified_tax_id:
                tax_range = record.env["l10n_br_fiscal.simplified.tax.range"].search(
                    [
                        ("simplified_tax_id", "=", simplified_tax_id.id),
                        ("inital_revenue", "<=", record.annual_revenue),
                        ("final_revenue", ">=", record.annual_revenue),
                        ("simplified_tax_id.coefficient_r", "=", record.coefficient_r),
                    ],
                    limit=1,
                )
                record.simplified_tax_range_id = tax_range

                if record.simplified_tax_range_id and record.annual_revenue:
                    record.simplified_tax_percent = round(
                        (
                            (
                                (
                                    record.annual_revenue
                                    * record.simplified_tax_range_id.total_tax_percent
                                    / 100
                                )
                                - record.simplified_tax_range_id.amount_deduced
                            )
                            / record.annual_revenue
                        )
                        * 100,
                        record.currency_id.decimal_places,
                    )

    legal_nature_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.legal.nature",
        string="Legal Nature",
        compute="_compute_address",
        inverse="_inverse_legal_nature_id",
    )

    cnae_main_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        compute="_compute_address",
        inverse="_inverse_cnae_main_id",
        domain="[('internal_type', '=', 'normal'), "
        "('id', 'not in', cnae_secondary_ids)]",
        string="Main CNAE",
    )

    cnae_secondary_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.cnae",
        relation="res_company_fiscal_cnae_rel",
        column1="company_id",
        column2="cnae_id",
        domain="[('internal_type', '=', 'normal'), " "('id', '!=', cnae_main_id)]",
        string="Secondary CNAE",
    )

    tax_framework = fields.Selection(
        selection=TAX_FRAMEWORK,
        default=TAX_FRAMEWORK_NORMAL,
        compute="_compute_address",
        inverse="_inverse_tax_framework",
    )

    profit_calculation = fields.Selection(
        selection=PROFIT_CALCULATION,
        default=PROFIT_CALCULATION_PRESUMED,
    )

    is_industry = fields.Boolean(
        help="If your company is industry or ......",
        default=False,
    )

    industry_type = fields.Selection(
        selection=INDUSTRY_TYPE,
        default=INDUSTRY_TYPE_TRANSFORMATION,
    )

    annual_revenue = fields.Monetary(
        currency_field="currency_id",
    )

    simplified_tax_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.simplified.tax",
        compute="_compute_simplified_tax",
        string="Simplified Tax",
        store=True,
        readonly=True,
    )

    simplified_tax_range_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.simplified.tax.range",
        compute="_compute_simplified_tax",
        store=True,
        readonly=True,
        string="Simplified Tax Range",
    )

    simplified_tax_percent = fields.Float(
        compute="_compute_simplified_tax",
        store=True,
        digits="Fiscal Tax Percent",
    )

    payroll_amount = fields.Monetary(
        string="Last Period Payroll Amount",
        currency_field="currency_id",
    )

    coefficient_r = fields.Boolean(
        compute="_compute_simplified_tax",
        store=True,
        readonly=True,
    )

    coefficient_r_percent = fields.Float(
        compute="_compute_simplified_tax",
        string="Coefficient R (%)",
        store=True,
        readonly=True,
    )

    ibpt_api = fields.Boolean(string="Use IBPT API", default=False)

    ibpt_token = fields.Char()

    ibpt_update_days = fields.Integer(string="IBPT Token Updates", default=15)

    accountant_id = fields.Many2one(comodel_name="res.partner", string="Accountant")

    accounting_office = fields.Many2one(comodel_name="res.partner")

    technical_support_id = fields.Many2one(
        comodel_name="res.partner", string="Technical Support"
    )

    piscofins_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax.pis.cofins",
        string="PIS/COFINS",
        domain="[('piscofins_type', '=', 'company')]",
    )

    tax_cofins_wh_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default COFINS RET",
        domain=[("tax_domain", "=", TAX_DOMAIN_COFINS_WH)],
    )

    tax_pis_wh_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default PIS RET",
        domain=[("tax_domain", "=", TAX_DOMAIN_PIS_WH)],
    )

    tax_csll_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default CSLL",
        domain=[("tax_domain", "=", TAX_DOMAIN_CSLL)],
    )

    tax_csll_wh_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default CSLL RET",
        domain=[("tax_domain", "=", TAX_DOMAIN_CSLL_WH)],
    )

    ripi = fields.Boolean(string="RIPI")

    tax_ipi_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default IPI",
        domain=[("tax_domain", "=", TAX_DOMAIN_IPI)],
    )

    tax_icms_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default ICMS",
        domain=[("tax_domain", "in", (TAX_DOMAIN_ICMS, TAX_DOMAIN_ICMS_SN))],
    )

    icms_regulation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.icms.regulation", string="ICMS Regulation"
    )

    tax_issqn_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default ISSQN",
        domain=[("tax_domain", "=", TAX_DOMAIN_ISSQN)],
    )

    tax_issqn_wh_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default ISSQN RET",
        domain=[("tax_domain", "=", TAX_DOMAIN_ISSQN_WH)],
    )

    tax_irpj_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default IRPJ",
        domain=[("tax_domain", "=", TAX_DOMAIN_IRPJ)],
    )

    tax_irpj_wh_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default IRPJ RET",
        domain=[("tax_domain", "=", TAX_DOMAIN_IRPJ_WH)],
    )

    tax_inss_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default INSS",
        domain=[("tax_domain", "=", TAX_DOMAIN_INSS)],
    )

    tax_inss_wh_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Default INSS RET",
        domain=[("tax_domain", "=", TAX_DOMAIN_INSS_WH)],
    )

    tax_classification_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax.classification",
        string="Default Tax Classification",
        domain=[("tax_ibs_id", "!=", False), ("tax_cbs_id", "!=", False)],
    )

    tax_definition_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.tax.definition",
        inverse_name="company_id",
        string="Tax Definition",
    )

    processador_edoc = fields.Selection(
        selection=PROCESSADOR,
        string="Processador documentos eletrônicos",
        default=PROCESSADOR_NENHUM,
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type", string="Default Document Type"
    )

    document_email_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.document.email",
        inverse_name="company_id",
        string="Email Template Definition",
    )

    document_save_disk = fields.Boolean(
        string="Save Documents to disk",
        default=True,
    )

    delivery_costs = fields.Selection(
        selection=[("line", "By Line"), ("total", "By Total")],
        help="Define if costs of Insurance, Freight and Other Costs"
        " should be informed by Line or by Total.",
        default="line",
    )

    anonymous_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Anonymous Partner",
        help="Partner used to create anonymous fiscal documents",
    )

    def _del_tax_definition(self, tax_domain):
        tax_def = self.tax_definition_ids.filtered(
            lambda d: d.tax_group_id.tax_domain != tax_domain
        )
        self.tax_definition_ids = tax_def

    def _set_tax_definition(self, tax):
        tax_def = self.tax_definition_ids.filtered(
            lambda d: d.tax_group_id == tax.tax_group_id
        )

        tax_def_values = {
            "type_in_out": "out",
            "tax_group_id": tax.tax_group_id.id,
            "is_taxed": True,
            "is_debit_credit": True,
            "custom_tax": True,
            "tax_id": tax.id,
            "cst_id": tax.cst_out_id.id,
            "company_id": self._origin.id,
        }

        if tax_def:
            tax_def.update(tax_def_values)
        else:
            self.tax_definition_ids |= self.tax_definition_ids.create(tax_def_values)

    @api.onchange("profit_calculation", "tax_framework")
    def _onchange_profit_calculation(self):
        # Get all Simples Nacional default taxes
        sn_piscofins_id = self.env.ref("l10n_br_fiscal.tax_pis_cofins_simples_nacional")

        sn_tax_icms_id = self.env.ref("l10n_br_fiscal.tax_icms_sn_com_credito")

        # If Tax Framework is Simples Nacional
        if self.tax_framework in TAX_FRAMEWORK_SIMPLES_ALL:
            # Set taxes
            self.piscofins_id = sn_piscofins_id
            self.tax_icms_id = sn_tax_icms_id

        # If Tax Framework is Regine Normal
        if self.tax_framework == TAX_FRAMEWORK_NORMAL:
            pis_cofins_refs = {
                "real": self.env.ref("l10n_br_fiscal.tax_pis_cofins_nao_columativo"),
                "presumed": self.env.ref("l10n_br_fiscal.tax_pis_cofins_columativo"),
                "arbitrary": self.env.ref("l10n_br_fiscal.tax_pis_cofins_columativo"),
            }

            self.piscofins_id = pis_cofins_refs.get(self.profit_calculation)
            self.tax_icms_id = False

        self._onchange_piscofins_id()
        self._onchange_tax_classification_id()
        self._onchange_ripi()
        self._onchange_tax_ipi_id()
        self._onchange_tax_icms_id()
        self._onchange_tax_issqn_id()
        self._onchange_tax_csll_id()
        self._onchange_tax_irpj_id()
        self._onchange_tax_inss_id()

        self._onchange_tax_issqn_wh_id()
        self._onchange_tax_pis_wh_id()
        self._onchange_tax_cofins_wh_id()
        self._onchange_tax_csll_wh_id()
        self._onchange_tax_irpj_wh_id()
        self._onchange_tax_inss_wh_id()

    @api.onchange("is_industry")
    def _onchange_is_industry(self):
        if self.is_industry and self.tax_framework == TAX_FRAMEWORK_SIMPLES:
            self.ripi = True
        else:
            self.ripi = False

    @api.onchange("ripi")
    def _onchange_ripi(self):
        if not self.ripi and self.tax_framework == TAX_FRAMEWORK_NORMAL:
            self.tax_ipi_id = self.env.ref("l10n_br_fiscal.tax_ipi_nt")
        elif self.tax_framework in TAX_FRAMEWORK_SIMPLES_ALL:
            self.tax_ipi_id = self.env.ref("l10n_br_fiscal.tax_ipi_outros")
            self.ripi = False
        else:
            self.tax_ipi_id = False

    @api.onchange("piscofins_id")
    def _onchange_piscofins_id(self):
        if self.piscofins_id:
            self._set_tax_definition(self.piscofins_id.tax_cofins_id)
            self._set_tax_definition(self.piscofins_id.tax_pis_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_PIS)
            self._del_tax_definition(TAX_DOMAIN_COFINS)

    @api.onchange("tax_pis_wh_id")
    def _onchange_tax_pis_wh_id(self):
        if self.tax_pis_wh_id:
            self._set_tax_definition(self.tax_pis_wh_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_PIS_WH)

    @api.onchange("tax_cofins_wh_id")
    def _onchange_tax_cofins_wh_id(self):
        if self.tax_cofins_wh_id:
            self._set_tax_definition(self.tax_cofins_wh_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_COFINS_WH)

    @api.onchange("tax_csll_id")
    def _onchange_tax_csll_id(self):
        if self.tax_csll_id:
            self._set_tax_definition(self.tax_csll_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_CSLL)

    @api.onchange("tax_csll_wh_id")
    def _onchange_tax_csll_wh_id(self):
        if self.tax_csll_wh_id:
            self._set_tax_definition(self.tax_csll_wh_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_CSLL_WH)

    @api.onchange("tax_ipi_id")
    def _onchange_tax_ipi_id(self):
        if self.tax_ipi_id:
            self._set_tax_definition(self.tax_ipi_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_IPI)

    @api.onchange("tax_icms_id")
    def _onchange_tax_icms_id(self):
        if self.tax_icms_id:
            self._set_tax_definition(self.tax_icms_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_ICMS)
            self._del_tax_definition(TAX_DOMAIN_ICMS_SN)

    @api.onchange("tax_issqn_id")
    def _onchange_tax_issqn_id(self):
        if self.tax_issqn_id:
            self._set_tax_definition(self.tax_issqn_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_ISSQN)

    @api.onchange("tax_issqn_wh_id")
    def _onchange_tax_issqn_wh_id(self):
        if self.tax_issqn_wh_id:
            self._set_tax_definition(self.tax_issqn_wh_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_ISSQN_WH)

    @api.onchange("tax_irpj_id")
    def _onchange_tax_irpj_id(self):
        if self.tax_irpj_id:
            self._set_tax_definition(self.tax_irpj_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_IRPJ)

    @api.onchange("tax_irpj_wh_id")
    def _onchange_tax_irpj_wh_id(self):
        if self.tax_irpj_wh_id:
            self._set_tax_definition(self.tax_irpj_wh_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_IRPJ_WH)

    @api.onchange("tax_inss_id")
    def _onchange_tax_inss_id(self):
        if self.tax_inss_id:
            self._set_tax_definition(self.tax_inss_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_INSS)

    @api.onchange("tax_inss_wh_id")
    def _onchange_tax_inss_wh_id(self):
        if self.tax_inss_wh_id:
            self._set_tax_definition(self.tax_inss_wh_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_INSS_WH)

    @api.onchange("tax_classification_id")
    def _onchange_tax_classification_id(self):
        if self.tax_classification_id:
            self._set_tax_definition(self.tax_classification_id.tax_cbs_id)
            self._set_tax_definition(self.tax_classification_id.tax_ibs_id)
        else:
            self._del_tax_definition(TAX_DOMAIN_CBS)
            self._del_tax_definition(TAX_DOMAIN_IBS)
