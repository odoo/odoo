# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from copy import deepcopy

from lxml import etree

from odoo import api, models

from ..constants.fiscal import CFOP_DESTINATION_EXPORT, FISCAL_IN
from ..constants.icms import ICMS_BASE_TYPE_DEFAULT, ICMS_ST_BASE_TYPE_DEFAULT
from .tax import TAX_DICT_VALUES

FISCAL_TAX_ID_FIELDS = [
    "cofins_tax_id",
    "cofins_wh_tax_id",
    "cofinsst_tax_id",
    "csll_tax_id",
    "csll_wh_tax_id",
    "icms_tax_id",
    "icmsfcp_tax_id",
    "icmssn_tax_id",
    "icmsst_tax_id",
    "icmsfcpst_tax_id",
    "ii_tax_id",
    "inss_tax_id",
    "inss_wh_tax_id",
    "ipi_tax_id",
    "irpj_tax_id",
    "irpj_wh_tax_id",
    "issqn_tax_id",
    "issqn_wh_tax_id",
    "pis_tax_id",
    "pis_wh_tax_id",
    "pisst_tax_id",
    "cbs_tax_id",
    "ibs_tax_id",
]

FISCAL_CST_ID_FIELDS = [
    "icms_cst_id",
    "ipi_cst_id",
    "pis_cst_id",
    "pisst_cst_id",
    "cofins_cst_id",
    "cofinsst_cst_id",
    "ibs_cst_id",
    "cbs_cst_id",
]


class FiscalDocumentLineMixinMethods(models.AbstractModel):
    _name = "l10n_br_fiscal.document.line.mixin.methods"
    _description = "Fiscal Document Mixin Methods"

    @api.model
    def inject_fiscal_fields(
        self,
        view_arch,
        view_ref="l10n_br_fiscal.document_fiscal_line_mixin_form",
        xpath_mappings=None,
    ):
        """
        Injects common fiscal fields into view placeholder elements.
        Used for invoice line, sale order line, purchase order line...
        """
        fiscal_view = self.env.ref(
            "l10n_br_fiscal.document_fiscal_line_mixin_form"
        ).sudo()
        fsc_doc = etree.fromstring(
            fiscal_view.with_context(inherit_branding=True).read_combined(["arch"])[
                "arch"
            ]
        )
        doc = etree.fromstring(view_arch)

        if xpath_mappings is None:
            xpath_mappings = (
                # (placeholder_xpath, fiscal_xpath)
                (".//group[@name='fiscal_fields']", "//group[@name='fiscal_fields']"),
                (".//page[@name='fiscal_taxes']", "//page[@name='fiscal_taxes']"),
                (
                    ".//page[@name='fiscal_line_extra_info']",
                    "//page[@name='fiscal_line_extra_info']",
                ),
                # these will only collect (invisible) fields for onchanges:
                (
                    ".//control[@name='fiscal_taxes_fields']...",
                    "//page[@name='fiscal_taxes']//field",
                ),
                (
                    ".//control[@name='fiscal_line_extra_info_fields']...",
                    "//page[@name='fiscal_line_extra_info']//field",
                ),
            )
        for placeholder_xpath, fiscal_xpath in xpath_mappings:
            fiscal_nodes = fsc_doc.xpath(fiscal_xpath)
            for target_node in doc.findall(placeholder_xpath):
                if len(fiscal_nodes) == 1:
                    # replace unique placeholder
                    # (deepcopy is required to inject fiscal nodes in possible
                    # next places)
                    replace_node = deepcopy(fiscal_nodes[0])
                    target_node.getparent().replace(target_node, replace_node)
                else:
                    # append multiple fields to placeholder container
                    for fiscal_node in fiscal_nodes:
                        field = deepcopy(fiscal_node)
                        if not field.attrib.get("optional"):
                            field.attrib["invisible"] = "1"
                        target_node.append(field)
        return doc

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        model_view = super().fields_view_get(view_id, view_type, toolbar, submenu)
        if view_type == "form":
            arch_tree = self.inject_fiscal_fields(model_view["arch"])
            View = self.env["ir.ui.view"]
            # Override context for postprocessing
            if view_id and model_view.get("base_model", self._name) != self._name:
                View = View.with_context(base_model_name=model_view["base_model"])

            # Apply post processing, groups and modifiers etc...
            xarch, xfields = View.postprocess_and_fields(
                node=arch_tree, model=self._name
            )
            model_view["arch"] = xarch
            model_view["fields"] = xfields
        return model_view

    @api.depends(
        "fiscal_price",
        "discount_value",
        "insurance_value",
        "other_value",
        "freight_value",
        "fiscal_quantity",
        "amount_tax_not_included",
        "amount_tax_included",
        "amount_tax_withholding",
        "uot_id",
        "product_id",
        "partner_id",
        "company_id",
        "price_unit",
        "quantity",
    )
    def _compute_amounts(self):
        for record in self:
            round_curr = record.currency_id or self.env.ref("base.BRL")

            # Total value of products or services
            record.price_gross = round_curr.round(record.price_unit * record.quantity)

            record.amount_untaxed = record.price_gross - record.discount_value

            record.amount_fiscal = record.price_gross - record.discount_value

            record.amount_tax = record.amount_tax_not_included

            add_to_amount = sum([record[a] for a in record._add_fields_to_amount()])
            rm_to_amount = sum([record[r] for r in record._rm_fields_to_amount()])

            # Valor do documento (NF)
            record.amount_total = (
                record.amount_untaxed + record.amount_tax + add_to_amount - rm_to_amount
            )

            # Valor Liquido (TOTAL + IMPOSTOS - RETENÇÕES)
            record.amount_taxed = record.amount_total - record.amount_tax_withholding

            # Valor do documento (NF) - RETENÇÕES
            record.amount_total = record.amount_taxed

            # Valor financeiro
            if (
                record.fiscal_operation_line_id
                and record.fiscal_operation_line_id.add_to_amount
                and (not record.cfop_id or record.cfop_id.finance_move)
            ):
                record.financial_total = record.amount_taxed
                record.financial_total_gross = (
                    record.financial_total + record.discount_value
                )
                record.financial_discount_value = record.discount_value
            else:
                record.financial_total_gross = record.financial_total = 0.0
                record.financial_discount_value = 0.0

    def _compute_taxes(self, taxes, cst=None):
        self.ensure_one()
        return taxes.compute_taxes(
            company=self.company_id,
            partner=self._get_fiscal_partner(),
            product=self.product_id,
            price_unit=self.price_unit,
            quantity=self.quantity,
            uom_id=self.uom_id,
            fiscal_price=self.fiscal_price,
            fiscal_quantity=self.fiscal_quantity,
            uot_id=self.uot_id,
            discount_value=self.discount_value,
            insurance_value=self.insurance_value,
            ii_customhouse_charges=self.ii_customhouse_charges,
            ii_iof_value=self.ii_iof_value,
            other_value=self.other_value,
            freight_value=self.freight_value,
            ncm=self.ncm_id,
            nbs=self.nbs_id,
            nbm=self.nbm_id,
            cest=self.cest_id,
            operation_line=self.fiscal_operation_line_id,
            cfop=self.cfop_id,
            icmssn_range=self.icmssn_range_id,
            icms_origin=self.icms_origin,
            icms_cst_id=self.icms_cst_id,
            ind_final=self.ind_final,
            icms_relief_id=self.icms_relief_id,
        )

    @api.depends("tax_icms_or_issqn", "partner_is_public_entity")
    def _compute_allow_csll_irpj(self):
        """Calculates the possibility of 'CSLL' and 'IRPJ' tax charges."""
        for line in self:
            # Determine if 'CSLL' and 'IRPJ' taxes may apply:
            # 1. When providing services (tax_icms_or_issqn == "issqn")
            # 2. When supplying products to public entities (partner_is_public_entity
            #  is True)
            if line.tax_icms_or_issqn == "issqn" or line.partner_is_public_entity:
                line.allow_csll_irpj = True  # Tax charges may apply
            else:
                line.allow_csll_irpj = False  # No tax charges expected

    @api.depends("tax_classification_id")
    def _compute_cst_code_prefix_like(self):
        for rec in self:
            code = rec.tax_classification_id.code if rec.tax_classification_id else ""
            prefix = (code or "")[:3]
            # Avoid matching all records when the prefix is not available yet.
            rec.cst_code_prefix_like = (
                f"{prefix}%" if len(prefix) == 3 else "__no_match__%"
            )

    def _prepare_br_fiscal_dict(self, default=False):
        self.ensure_one()
        fields = self.env["l10n_br_fiscal.document.line.mixin"]._fields.keys()

        # we now read the record fiscal fields except the m2m tax:
        vals = self._convert_to_write(self.read(fields)[0])

        # remove id field to avoid conflicts
        vals.pop("id", None)

        if default:  # in case you want to use new rather than write later
            return {f"default_{k}": vals[k] for k in vals.keys()}
        return vals

    def _get_all_tax_id_fields(self):
        self.ensure_one()
        taxes = self.env["l10n_br_fiscal.tax"]

        for fiscal_tax_field in FISCAL_TAX_ID_FIELDS:
            taxes |= self[fiscal_tax_field]

        return taxes

    def _remove_all_fiscal_tax_ids(self):
        for line in self:
            to_update = {"fiscal_tax_ids": False}
            for fiscal_tax_field in FISCAL_TAX_ID_FIELDS:
                to_update[fiscal_tax_field] = False
            tax_methods = [
                self._prepare_fields_issqn,
                self._prepare_fields_csll,
                self._prepare_fields_irpj,
                self._prepare_fields_inss,
                self._prepare_fields_icms,
                self._prepare_fields_icmsfcp,
                self._prepare_fields_icmsfcpst,
                self._prepare_fields_icmsst,
                self._prepare_fields_icmssn,
                self._prepare_fields_ipi,
                self._prepare_fields_ii,
                self._prepare_fields_pis,
                self._prepare_fields_pisst,
                self._prepare_fields_cofins,
                self._prepare_fields_cofinsst,
                self._prepare_fields_issqn_wh,
                self._prepare_fields_pis_wh,
                self._prepare_fields_cofins_wh,
                self._prepare_fields_csll_wh,
                self._prepare_fields_irpj_wh,
                self._prepare_fields_inss_wh,
                self._prepare_fields_ibs,
                self._prepare_fields_cbs,
            ]
            for method in tax_methods:
                prepared_fields = method(TAX_DICT_VALUES)
                if prepared_fields:
                    to_update.update(prepared_fields)
            # Update all fields at once
            line.update(to_update)

    def _update_fiscal_tax_ids(self, taxes):
        for line in self:
            taxes_groups = line.fiscal_tax_ids.mapped("tax_domain")
            fiscal_taxes = line.fiscal_tax_ids.filtered(
                lambda ft, taxes_groups=taxes_groups: ft.tax_domain not in taxes_groups
            )
            line.fiscal_tax_ids = fiscal_taxes + taxes

    def _update_fiscal_taxes(self):
        for line in self:
            compute_result = self._compute_taxes(line.fiscal_tax_ids)
            to_update = {
                "amount_tax_included": compute_result.get("amount_included", 0.0),
                "amount_tax_not_included": compute_result.get(
                    "amount_not_included", 0.0
                ),
                "amount_tax_withholding": compute_result.get("amount_withholding", 0.0),
                "estimate_tax": compute_result.get("estimate_tax", 0.0),
            }
            to_update.update(line._prepare_tax_fields(compute_result))

            in_draft_mode = self != self._origin
            if in_draft_mode:
                line.update(to_update)
            else:
                line.write(to_update)

    def _prepare_tax_fields(self, compute_result):
        self.ensure_one()
        computed_taxes = compute_result.get("taxes", {})
        tax_values = {}
        for tax in self.fiscal_tax_ids:
            computed_tax = computed_taxes.get(tax.tax_domain, {})
            tax_field_name = f"{tax.tax_domain}_tax_id"
            if hasattr(self, tax_field_name):
                tax_values[tax_field_name] = tax.ids[0]
                method = getattr(self, f"_prepare_fields_{tax.tax_domain}", None)
                if method and computed_tax:
                    prepared_fields = method(computed_tax)
                    if prepared_fields:
                        tax_values.update(prepared_fields)
        return tax_values

    def _get_product_price(self):
        self.ensure_one()
        price = {
            "sale_price": self.product_id.list_price,
            "cost_price": self.product_id.standard_price,
        }

        self.price_unit = price.get(self.fiscal_operation_id.default_price_unit, 0.00)

    def __document_comment_vals(self):
        self.ensure_one()
        return {
            "user": self.env.user,
            "ctx": self._context,
            "doc": self.document_id,
            "item": self,
        }

    def _document_comment(self):
        for d in self:
            d.additional_data = d.comment_ids.compute_message(
                d.__document_comment_vals(), d.manual_additional_data
            )

    def _get_fiscal_partner(self):
        """
        Meant to be overriden when the l10n_br_fiscal.document partner_id should not
        be the same as the sale.order, purchase.order, account.move (...) partner_id.

        (In the case of invoicing, the invoicing partner set by the user should
        get priority over any invoicing contact returned by address_get.)
        """
        self.ensure_one()
        return self.partner_id

    @api.onchange(
        "fiscal_operation_id", "ncm_id", "nbs_id", "cest_id", "service_type_id"
    )
    def _onchange_fiscal_operation_id(self):
        if self.fiscal_operation_id:
            if not self.price_unit:
                self._get_product_price()
            self._onchange_commercial_quantity()
            self.fiscal_operation_line_id = self.fiscal_operation_id.line_definition(
                company=self.company_id,
                partner=self._get_fiscal_partner(),
                product=self.product_id,
            )
            self._onchange_fiscal_operation_line_id()

    @api.onchange("fiscal_operation_line_id")
    def _onchange_fiscal_operation_line_id(self):
        # Reset Taxes
        self._remove_all_fiscal_tax_ids()
        if self.fiscal_operation_line_id:
            mapping_result = self.fiscal_operation_line_id.map_fiscal_taxes(
                company=self.company_id,
                partner=self._get_fiscal_partner(),
                product=self.product_id,
                ncm=self.ncm_id,
                nbm=self.nbm_id,
                nbs=self.nbs_id,
                cest=self.cest_id,
                city_taxation_code=self.city_taxation_code_id,
                national_taxation_code=self.national_taxation_code_id,
                service_type=self.service_type_id,
                ind_final=self.ind_final,
            )

            self.cfop_id = mapping_result["cfop"]
            self._process_fiscal_mapping(mapping_result)

        if not self.fiscal_operation_line_id:
            self.cfop_id = False

    def _process_fiscal_mapping(self, mapping_result):
        self.ipi_guideline_id = mapping_result["ipi_guideline"]
        self.tax_classification_id = mapping_result["tax_classification"]
        self.icms_tax_benefit_id = mapping_result["icms_tax_benefit_id"]
        taxes = self.env["l10n_br_fiscal.tax"]
        for tax in mapping_result["taxes"].values():
            taxes |= tax
        self.fiscal_tax_ids = taxes
        self._update_fiscal_taxes()
        self.comment_ids = self.fiscal_operation_line_id.comment_ids

    @api.onchange("product_id")
    def _onchange_product_id_fiscal(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.fiscal_type = self.product_id.fiscal_type
            self.uom_id = self.product_id.uom_id
            self.ncm_id = self.product_id.ncm_id
            self.nbm_id = self.product_id.nbm_id
            self.tax_icms_or_issqn = self.product_id.tax_icms_or_issqn
            self.icms_origin = self.product_id.icms_origin
            self.cest_id = self.product_id.cest_id
            self.nbs_id = self.product_id.nbs_id
            self.fiscal_genre_id = self.product_id.fiscal_genre_id
            self.service_type_id = self.product_id.service_type_id
            self.operation_indicator_id = self.product_id.operation_indicator_id
            self.uot_id = self.product_id.uot_id or self.product_id.uom_id
            if self.product_id.city_taxation_code_id:
                company_city_id = self.company_id.city_id
                city_id = self.product_id.city_taxation_code_id.filtered(
                    lambda r: r.city_id == company_city_id
                )
                if city_id:
                    self.city_taxation_code_id = city_id
                    self.issqn_fg_city_id = company_city_id
            if self.product_id.national_taxation_code_id:
                self.national_taxation_code_id = (
                    self.product_id.national_taxation_code_id
                )
        else:
            self.name = False
            self.fiscal_type = False
            self.uom_id = False
            self.ncm_id = False
            self.nbm_id = False
            self.tax_icms_or_issqn = False
            self.icms_origin = False
            self.cest_id = False
            self.nbs_id = False
            self.fiscal_genre_id = False
            self.service_type_id = False
            self.operation_indicator_id = False
            self.city_taxation_code_id = False
            self.national_taxation_code_id = False
            self.uot_id = False

        self._get_product_price()
        self._onchange_fiscal_operation_id()

    def _prepare_fields_issqn(self, tax_dict):
        self.ensure_one()
        return {
            "issqn_base": tax_dict.get("base"),
            "issqn_percent": tax_dict.get("percent_amount"),
            "issqn_reduction": tax_dict.get("percent_reduction"),
            "issqn_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_issqn_wh(self, tax_dict):
        self.ensure_one()
        return {
            "issqn_wh_base": tax_dict.get("base"),
            "issqn_wh_percent": tax_dict.get("percent_amount"),
            "issqn_wh_reduction": tax_dict.get("percent_reduction"),
            "issqn_wh_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_csll(self, tax_dict):
        self.ensure_one()
        return {
            "csll_base": tax_dict.get("base"),
            "csll_percent": tax_dict.get("percent_amount"),
            "csll_reduction": tax_dict.get("percent_reduction"),
            "csll_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_csll_wh(self, tax_dict):
        self.ensure_one()
        return {
            "csll_wh_base": tax_dict.get("base"),
            "csll_wh_percent": tax_dict.get("percent_amount"),
            "csll_wh_reduction": tax_dict.get("percent_reduction"),
            "csll_wh_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_irpj(self, tax_dict):
        self.ensure_one()
        return {
            "irpj_base": tax_dict.get("base"),
            "irpj_percent": tax_dict.get("percent_amount"),
            "irpj_reduction": tax_dict.get("percent_reduction"),
            "irpj_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_irpj_wh(self, tax_dict):
        self.ensure_one()
        return {
            "irpj_wh_base": tax_dict.get("base"),
            "irpj_wh_percent": tax_dict.get("percent_amount"),
            "irpj_wh_reduction": tax_dict.get("percent_reduction"),
            "irpj_wh_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_inss(self, tax_dict):
        self.ensure_one()
        return {
            "inss_base": tax_dict.get("base"),
            "inss_percent": tax_dict.get("percent_amount"),
            "inss_reduction": tax_dict.get("percent_reduction"),
            "inss_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_inss_wh(self, tax_dict):
        self.ensure_one()
        return {
            "inss_wh_base": tax_dict.get("base"),
            "inss_wh_percent": tax_dict.get("percent_amount"),
            "inss_wh_reduction": tax_dict.get("percent_reduction"),
            "inss_wh_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_icms(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "icms_cst_id": cst_id,
            "icms_base_type": tax_dict.get("icms_base_type", ICMS_BASE_TYPE_DEFAULT),
            "icms_base": tax_dict.get("base", 0.0),
            "icms_percent": tax_dict.get("percent_amount", 0.0),
            "icms_reduction": tax_dict.get("percent_reduction", 0.0),
            "icms_value": tax_dict.get("tax_value", 0.0),
            "icms_origin_percent": tax_dict.get("icms_origin_perc", 0.0),
            "icms_destination_percent": tax_dict.get("icms_dest_perc", 0.0),
            "icms_sharing_percent": tax_dict.get("icms_sharing_percent", 0.0),
            "icms_destination_base": tax_dict.get("icms_dest_base", 0.0),
            "icms_origin_value": tax_dict.get("icms_origin_value", 0.0),
            "icms_destination_value": tax_dict.get("icms_dest_value", 0.0),
            "icms_relief_value": tax_dict.get("icms_relief", 0.0),
        }

    @api.onchange(
        "icms_base",
        "icms_percent",
        "icms_reduction",
        "icms_value",
        "icms_destination_base",
        "icms_origin_percent",
        "icms_destination_percent",
        "icms_sharing_percent",
        "icms_origin_value",
        "icms_tax_benefit_id",
    )
    def _onchange_icms_fields(self):
        if self.icms_tax_benefit_id:
            self.icms_tax_id = self.icms_tax_benefit_id.tax_id

    @api.onchange("tax_classification_id")
    def _onchange_tax_classification_id(self):
        if self.tax_classification_id:
            self.ibs_tax_id = self.tax_classification_id.tax_ibs_id
            self.cbs_tax_id = self.tax_classification_id.tax_cbs_id

    def _prepare_fields_icmssn(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        icmssn_base = tax_dict.get("base", 0.0)
        icmssn_credit_value = tax_dict.get("tax_value", 0.0)
        simple_value = icmssn_base * self.icmssn_range_id.total_tax_percent
        simple_without_icms_value = simple_value - icmssn_credit_value
        return {
            "icms_cst_id": cst_id,
            "icmssn_base": icmssn_base,
            "icmssn_percent": tax_dict.get("percent_amount"),
            "icmssn_reduction": tax_dict.get("percent_reduction"),
            "icmssn_credit_value": icmssn_credit_value,
            "simple_value": simple_value,
            "simple_without_icms_value": simple_without_icms_value,
        }

    def _prepare_fields_icmsst(self, tax_dict):
        self.ensure_one()
        return {
            "icmsst_base_type": tax_dict.get(
                "icmsst_base_type", ICMS_ST_BASE_TYPE_DEFAULT
            ),
            "icmsst_mva_percent": tax_dict.get("icmsst_mva_percent"),
            "icmsst_percent": tax_dict.get("percent_amount"),
            "icmsst_reduction": tax_dict.get("percent_reduction"),
            "icmsst_base": tax_dict.get("base"),
            "icmsst_value": tax_dict.get("tax_value"),
        }

    def _prepare_fields_icmsfcp(self, tax_dict):
        self.ensure_one()
        return {
            "icmsfcp_base": tax_dict.get("base", 0.0),
            "icmsfcp_percent": tax_dict.get("percent_amount", 0.0),
            "icmsfcp_value": tax_dict.get("tax_value", 0.0),
        }

    def _prepare_fields_icmsfcpst(self, tax_dict):
        self.ensure_one()
        return {
            "icmsfcpst_base": self.icmsst_base,
            "icmsfcpst_percent": tax_dict.get("percent_amount", 0.0),
            "icmsfcpst_value": tax_dict.get("tax_value", 0.0),
        }

    def _prepare_fields_ipi(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "ipi_cst_id": cst_id,
            "ipi_base_type": tax_dict.get("base_type", False),
            "ipi_base": tax_dict.get("base", 0.00),
            "ipi_percent": tax_dict.get("percent_amount", 0.00),
            "ipi_reduction": tax_dict.get("percent_reduction", 0.00),
            "ipi_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_ii(self, tax_dict):
        self.ensure_one()
        return {
            "ii_base": tax_dict.get("base", 0.00),
            "ii_percent": tax_dict.get("percent_amount", 0.00),
            "ii_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_pis(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "pis_cst_id": cst_id,
            "pis_base_type": tax_dict.get("base_type"),
            "pis_base": tax_dict.get("base", 0.00),
            "pis_percent": tax_dict.get("percent_amount", 0.00),
            "pis_reduction": tax_dict.get("percent_reduction", 0.00),
            "pis_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_cbs(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "cbs_cst_id": cst_id,
            "cbs_base_type": tax_dict.get("base_type"),
            "cbs_base": tax_dict.get("base", 0.00),
            "cbs_percent": tax_dict.get("percent_amount", 0.00),
            "cbs_reduction": tax_dict.get("percent_reduction", 0.00),
            "cbs_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_ibs(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "ibs_cst_id": cst_id,
            "ibs_base_type": tax_dict.get("base_type"),
            "ibs_base": tax_dict.get("base", 0.00),
            "ibs_percent": tax_dict.get("percent_amount", 0.00),
            "ibs_reduction": tax_dict.get("percent_reduction", 0.00),
            "ibs_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_pis_wh(self, tax_dict):
        self.ensure_one()
        return {
            "pis_wh_base_type": tax_dict.get("base_type"),
            "pis_wh_base": tax_dict.get("base", 0.00),
            "pis_wh_percent": tax_dict.get("percent_amount", 0.00),
            "pis_wh_reduction": tax_dict.get("percent_reduction", 0.00),
            "pis_wh_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_pisst(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "pisst_cst_id": cst_id,
            "pisst_base_type": tax_dict.get("base_type"),
            "pisst_base": tax_dict.get("base", 0.00),
            "pisst_percent": tax_dict.get("percent_amount", 0.00),
            "pisst_reduction": tax_dict.get("percent_reduction", 0.00),
            "pisst_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_cofins(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "cofins_cst_id": cst_id,
            "cofins_base_type": tax_dict.get("base_type"),
            "cofins_base": tax_dict.get("base", 0.00),
            "cofins_percent": tax_dict.get("percent_amount", 0.00),
            "cofins_reduction": tax_dict.get("percent_reduction", 0.00),
            "cofins_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_cofins_wh(self, tax_dict):
        self.ensure_one()
        return {
            "cofins_wh_base_type": tax_dict.get("base_type"),
            "cofins_wh_base": tax_dict.get("base", 0.00),
            "cofins_wh_percent": tax_dict.get("percent_amount", 0.00),
            "cofins_wh_reduction": tax_dict.get("percent_reduction", 0.00),
            "cofins_wh_value": tax_dict.get("tax_value", 0.00),
        }

    def _prepare_fields_cofinsst(self, tax_dict):
        self.ensure_one()
        cst_id = tax_dict.get("cst_id").id if tax_dict.get("cst_id") else False
        return {
            "cofinsst_cst_id": cst_id,
            "cofinsst_base_type": tax_dict.get("base_type"),
            "cofinsst_base": tax_dict.get("base", 0.00),
            "cofinsst_percent": tax_dict.get("percent_amount", 0.00),
            "cofinsst_reduction": tax_dict.get("percent_reduction", 0.00),
            "cofinsst_value": tax_dict.get("tax_value", 0.00),
        }

    @api.onchange(
        "csll_tax_id",
        "csll_wh_tax_id",
        "irpj_tax_id",
        "irpj_wh_tax_id",
        "inss_tax_id",
        "inss_wh_tax_id",
        "issqn_tax_id",
        "issqn_wh_tax_id",
        "icms_tax_id",
        "icmssn_tax_id",
        "icmsst_tax_id",
        "icmsfcp_tax_id",
        "icmsfcpst_tax_id",
        "icms_relief_id",
        "icms_relief_value",
        "ipi_tax_id",
        "ii_tax_id",
        "pis_tax_id",
        "pis_wh_tax_id",
        "pisst_tax_id",
        "cofins_tax_id",
        "cofins_wh_tax_id",
        "cofinsst_tax_id",
        "ibs_tax_id",
        "cbs_tax_id",
        "fiscal_price",
        "fiscal_quantity",
        "discount_value",
        "insurance_value",
        "other_value",
        "freight_value",
    )
    def _onchange_fiscal_taxes(self):
        self._update_fiscal_tax_ids(self._get_all_tax_id_fields())
        self._update_fiscal_taxes()

    @api.model
    def _update_fiscal_quantity(self, product_id, price, quantity, uom_id, uot_id):
        result = {"uot_id": uom_id, "fiscal_quantity": quantity, "fiscal_price": price}
        if uot_id and uom_id != uot_id:
            result["uot_id"] = uot_id
            if product_id and price and quantity:
                product = self.env["product.product"].browse(product_id)
                result["fiscal_price"] = price / (product.uot_factor or 1.0)
                result["fiscal_quantity"] = quantity * (product.uot_factor or 1.0)

        return result

    @api.onchange("uot_id", "uom_id", "price_unit", "quantity")
    def _onchange_commercial_quantity(self):
        product_id = False
        if self.product_id:
            product_id = self.product_id.id
        self.update(
            self._update_fiscal_quantity(
                product_id, self.price_unit, self.quantity, self.uom_id, self.uot_id
            )
        )

    @api.onchange("ii_customhouse_charges")
    def _onchange_ii_customhouse_charges(self):
        if self.ii_customhouse_charges:
            self._update_fiscal_taxes()

    @api.onchange("fiscal_tax_ids")
    def _onchange_fiscal_tax_ids(self):
        self._update_fiscal_taxes()

    @api.onchange("city_taxation_code_id")
    def _onchange_city_taxation_code_id(self):
        if self.city_taxation_code_id:
            self.cnae_id = self.city_taxation_code_id.cnae_id
            self._onchange_fiscal_operation_id()
            if self.city_taxation_code_id.city_id:
                self.update({"issqn_fg_city_id": self.city_taxation_code_id.city_id})

    @api.model
    def _add_fields_to_amount(self):
        fields_to_amount = ["insurance_value", "other_value", "freight_value"]
        if (
            self.cfop_id.destination == CFOP_DESTINATION_EXPORT
            and self.fiscal_operation_id.fiscal_operation_type == FISCAL_IN
        ):
            fields_to_amount.append("pis_value")
            fields_to_amount.append("cofins_value")
            fields_to_amount.append("icms_value")
            fields_to_amount.append("ii_value")
            fields_to_amount.append("ii_customhouse_charges")
        return fields_to_amount

    @api.model
    def _rm_fields_to_amount(self):
        return ["icms_relief_value"]
