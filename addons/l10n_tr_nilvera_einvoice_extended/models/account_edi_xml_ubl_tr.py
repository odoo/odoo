from lxml import etree
from collections import defaultdict
import copy

from odoo import models


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = "account.edi.xml.ubl.tr"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_vals(self, invoice):
        """Extend export invoice values with Turkish-specific attributes and templates.

        - Adds invoice profile and document type based on Turkish localization fields.
        - Specifies custom XML templates for invoice lines and deliveries.

        :param invoice: The invoice record to export.
        :return: A dictionary of exported values.
        """
        vals = super()._export_invoice_vals(invoice)
        if invoice.move_type != "out_invoice":
            return vals

        vals["vals"].update({"profile_id": self._get_tr_profile_id(invoice)})
        vals["vals"].update({"document_type_code": invoice.l10n_tr_gib_invoice_type})
        if invoice.l10n_tr_is_export_invoice:
            municipality_partner = self.env.ref(
                "l10n_tr_nilvera_einvoice_extended.l10n_tr_res_partner_municipality"
            )

            # We will have to update buyer_customer_party_vals to have PARTYTYPE
            # We can't do it from _get_partner_party_vals as we don't have the
            # scenario of the invoice inside that function so we
            # Prepare buyer_customer_party_vals from existing customer party
            buyer_customer_party_vals = vals["vals"]["accounting_customer_party_vals"]

            # Update party identification for export
            buyer_customer_party_vals["party_vals"]["party_identification_vals"] = [
                {
                    "id_attrs": {"schemeID": "PARTYTYPE"},
                    "id": "EXPORT",
                }
            ]

            # Update invoice values
            vals["vals"].update(
                {
                    "document_type_code": "ISTISNA",
                    "buyer_customer_party_vals": buyer_customer_party_vals,
                    "accounting_customer_party_vals": {
                        "party_vals": self._get_partner_party_vals(
                            municipality_partner,
                            role="tr_municipality",
                        )
                    },
                }
            )

            # Set invoice type template
            vals["InvoiceType_template"] = (
                "l10n_tr_nilvera_einvoice_extended.ubl_tr_export_InvoiceType"
            )
        elif invoice.l10n_tr_gib_invoice_type == "TEVKIFAT":
            vals["vals"].update(
                {
                    "withholding_tax_total_vals_list": self._tr_tax_totals(
                        invoice, vals["taxes_vals"], withholding=True
                    ),
                }
            )
        vals.update(
            {
                "InvoiceLineType_template": "l10n_tr_nilvera_einvoice_extended.ubl_tr_InvoiceLineType",
                "InvoiceLineDelivery_template": "l10n_tr_nilvera_einvoice_extended.ubl_tr_LineDelivery",
            }
        )

        return vals

    def _get_partner_party_vals(self, partner, role):
        if role == "tr_municipality":
            return self._get_tr_municipality_vals(partner)
        return super()._get_partner_party_vals(partner, role)

    def _get_tr_municipality_vals(self, partner):
        return {
            "partner": partner,
            "party_identification_vals": self._get_partner_party_identification_vals_list(
                partner.commercial_partner_id
            ),
            "party_name_vals": [{"name": partner.display_name}],
            "postal_address_vals": self._get_partner_address_vals(partner),
            "party_tax_scheme_vals": [{"tax_scheme_vals": {"name": "Ulus"}}],
        }

    def _get_tr_profile_id(self, invoice):
        if (
            invoice.l10n_tr_gib_invoice_scenario
            and invoice.l10n_tr_nilvera_customer_status == "einvoice"
        ):
            return invoice.l10n_tr_gib_invoice_scenario
        elif invoice.l10n_tr_is_export_invoice:
            return "IHRACAT"
        return "EARSIVFATURA"

    def _get_tax_category_list(self, customer, supplier, taxes):
        """Extend tax category list to include Turkish withholding tax codes.

        Filters out withholding taxes from the main list and appends them separately
        with Turkish-specific tax scheme values.

        :param customer: The partner receiving the invoice.
        :param supplier: The partner issuing the invoice.
        :param taxes: Recordset of taxes.
        :return: A list of tax category values.
        """
        res = super()._get_tax_category_list(
            customer,
            supplier,
            taxes.filtered(lambda t: not t.l10n_tr_tax_withholding_code_id),
        )
        for tax in taxes.filtered(lambda t: t.l10n_tr_tax_withholding_code_id):
            tax_type_code = tax.l10n_tr_tax_withholding_code_id.code or "0015"
            tax_scheme_name = (
                tax.l10n_tr_tax_withholding_code_id.with_context(lang="tr_TR").name
                or "Gerçek Usulde KDV"
            )
            res.append(
                {
                    "id": tax_type_code,
                    "percent": tax.l10n_tr_tax_withholding_code_id.percentage or False,
                    "tax_scheme_vals": {
                        "name": tax_scheme_name,
                        "tax_type_code": tax_type_code,
                    },
                }
            )
        return res

    def _get_tax_grouping_key(self, base_line, tax_data):
        """Extend tax grouping key to include Turkish withholding tax metadata.

        Adds exemption reason and withholding-related fields required for UBL withholding e-Invoice
        generation in Turkey. Applies tax scheme details if the invoice is of type TEVKIFAT.

        :param base_line: Dictionary representing a line being processed for tax.
        :param tax_data: Dictionary with tax rule and computed values.
        :return: Updated tax grouping key including Turkish-specific withholding tax metadata.
        """
        # EXTENDS account.edi.xml.ubl_20
        grouping_key = super()._get_tax_grouping_key(base_line, tax_data)
        invoice = base_line["record"].move_id
        tax = tax_data["tax"]
        grouping_key["_tax_category_vals_"]["l10n_tr_tax_exemption_reason"] = (
            tax.l10n_tr_tax_withholding_code_id.id
        )
        if (
            invoice.l10n_tr_gib_invoice_type == "TEVKIFAT"
            and tax.l10n_tr_tax_withholding_code_id
        ):
            grouping_key["tax_category_id"] = tax.l10n_tr_tax_withholding_code_id.id
            grouping_key["_tax_category_vals_"]["id"] = (
                tax.l10n_tr_tax_withholding_code_id.code
            )
            grouping_key["_tax_category_vals_"]["percent_withheld"] = (
                tax.l10n_tr_tax_withholding_code_id.percentage
            )
            grouping_key["_tax_category_vals_"]["tax_scheme_vals"]["name"] = (
                tax.l10n_tr_tax_withholding_code_id.with_context(lang="tr_TR").name
            )
            grouping_key["_tax_category_vals_"]["tax_scheme_vals"]["tax_type_code"] = (
                tax.l10n_tr_tax_withholding_code_id.code
            )

        return grouping_key

    def _tr_tax_totals(self, invoice, taxes_vals, withholding):
        """Build Turkish UBL-compliant tax totals for e-Invoice Withholding Senario Only.

        Filters and structures tax subtotal values based on whether the invoice
        includes withholding taxes. Handles early payment discounts (EPD) and ensures
        proper formatting of tax categories for UBL export.

        - Filters tax lines by exemption reason based on withholding flag.
        - Computes and attaches withholding percentage when applicable.
        - Adjusts taxable amounts for early payment discounts.
        - Appends additional exemption subtotal if EPD is used.

        :param invoice: The account.move record representing the invoice.
        :param taxes_vals: Dictionary with tax calculation results.
        :param withholding: Boolean indicating if this is for a withholding invoice.
        :return: List containing a dictionary of structured tax totals.
        """

        def filter_tax_details(key):
            reason = key.get("_tax_category_vals_", {}).get(
                "l10n_tr_tax_exemption_reason"
            )
            return bool(reason) if withholding else not bool(reason)

        tax_totals_vals = {
            "currency": invoice.currency_id,
            "currency_dp": self._get_currency_decimal_places(invoice.currency_id),
            "tax_amount": taxes_vals["tax_amount_currency"],
            "tax_subtotal_vals": [],
        }

        # If it's not on the whole invoice, don't manage the EPD.
        epd_tax_to_discount = {}
        if not taxes_vals.get("invoice_line"):
            epd_tax_to_discount = self._get_early_payment_discount_grouped_by_tax_rate(
                invoice
            )
            epd_base_tax_amounts = defaultdict(
                lambda: {
                    "base_amount_currency": 0.0,
                    "tax_amount_currency": 0.0,
                }
            )
            if epd_tax_to_discount:
                for percentage, base_amount_currency in epd_tax_to_discount.items():
                    epd_base_tax_amounts[percentage]["base_amount_currency"] += (
                        base_amount_currency
                    )
                epd_accounted_tax_amount = 0.0
                for percentage, amounts in epd_base_tax_amounts.items():
                    amounts["tax_amount_currency"] = invoice.currency_id.round(
                        amounts["base_amount_currency"] * percentage / 100.0
                    )
                    epd_accounted_tax_amount += amounts["tax_amount_currency"]

        # UBL_TR: Filter tax lines based on exemption reason:
        # - If withholding → include only tax lines with an exemption reason
        # - If not withholding → include only tax lines without an exemption reason
        filtered_tax_details = {
            k: v for k, v in taxes_vals["tax_details"].items() if filter_tax_details(k)
        }
        for grouping_key, vals in filtered_tax_details.items():
            if grouping_key["tax_amount_type"] != "fixed" or not self._context.get(
                "convert_fixed_taxes"
            ):
                # UBL_TR: Prepare tax subtotal values
                # - Copy tax category data and sanitize it for export (remove ID and percent)
                # - For withholding taxes, compute and attach the withholding percentage as an integer
                tax_category_vals = vals.get("_tax_category_vals_", {}).copy()
                subtotal_percent = int(
                    tax_category_vals.get("percent_withheld", 0) * 100
                )
                tax_category_vals.update(
                    {
                        "id": False,
                        "percent": False,
                    }
                )

                subtotal = {
                    "currency": invoice.currency_id,
                    "currency_dp": self._get_currency_decimal_places(
                        invoice.currency_id
                    ),
                    "taxable_amount": vals.get("base_amount_currency"),
                    "tax_amount": abs(vals.get("tax_amount_currency")),
                    "tax_category_vals": tax_category_vals,
                }
                if withholding:
                    subtotal.update({"percent": subtotal_percent})
                if epd_tax_to_discount:
                    # early payment discounts: need to recompute the tax/taxable amounts
                    epd_base_amount = epd_base_tax_amounts.get(
                        subtotal["percent"], {}
                    ).get("base_amount_currency", 0.0)
                    taxable_amount_after_epd = (
                        subtotal["taxable_amount"] - epd_base_amount
                    )
                    subtotal.update(
                        {
                            "taxable_amount": taxable_amount_after_epd,
                        }
                    )
                tax_totals_vals["tax_subtotal_vals"].append(subtotal)

        if epd_tax_to_discount:
            # early payment discounts: hence, need to add a subtotal section
            tax_totals_vals["tax_subtotal_vals"].append(
                {
                    "currency": invoice.currency_id,
                    "currency_dp": invoice.currency_id.decimal_places,
                    "taxable_amount": sum(epd_tax_to_discount.values()),
                    "tax_amount": 0.0,
                    "tax_category_vals": {
                        "tax_scheme_vals": {
                            "id": "VAT",
                        },
                        "tax_exemption_reason": "Exempt from tax",
                    },
                }
            )
        return [tax_totals_vals]

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        """Extend tax totals to include Turkish exemption codes and reasons.

        Applies VAT exemption information to each tax subtotal if relevant.

        :param invoice: The invoice object.
        :param taxes_vals: Tax calculation values.
        :return: Updated tax totals values.
        """
        if invoice.l10n_tr_gib_invoice_type == "TEVKIFAT":
            return self._tr_tax_totals(invoice, taxes_vals, withholding=False)

        tax_totals_vals = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        tax_invoice_exemption = invoice.l10n_tr_exemption_code_id
        if self.env.context.get("skip_code") or not tax_invoice_exemption:
            return tax_totals_vals

        for vals in tax_totals_vals:
            for subtotal_vals in vals.get("tax_subtotal_vals", []):
                subtotal_vals.get("tax_category_vals", {})[
                    "tax_exemption_reason_code"
                ] = tax_invoice_exemption.code
                subtotal_vals.get("tax_category_vals", {})["tax_exemption_reason"] = (
                    tax_invoice_exemption.with_context(lang="tr_TR").name
                )
        return tax_totals_vals

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        """Bypass exemption logic during line-level tax calculation.

        This prevents unnecessary exemption assignment at the line level.

        :param line: The invoice line.
        :param taxes_vals: Tax values for the line.
        :return: Deep copied tax totals list.
        """
        tax_totals_vals = super(
            AccountEdiXmlUblTr, self.with_context(skip_code=True)
        )._get_invoice_line_tax_totals_vals_list(line, taxes_vals)
        return copy.deepcopy(tax_totals_vals)

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        """Extend line export values with delivery data for export invoices.

        Adds line-level delivery details if the invoice is marked as 'l10n_tr_is_export_invoice'.

        :param line: The invoice line.
        :param line_id: Line identifier.
        :param taxes_vals: Calculated tax values for the line.
        :return: A dictionary of invoice line values.
        """
        vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        if line.move_id.l10n_tr_is_export_invoice:
            vals["line_delivery_vals"] = self._get_invoice_line_delivery_vals(line)
        if line.move_id.l10n_tr_gib_invoice_type == "TEVKIFAT":
            vals.update(
                {
                    "withholding_tax_total_vals_list": self._tr_tax_totals(
                        line.move_id, taxes_vals, withholding=True
                    ),
                }
            )
        return vals

    def _get_invoice_line_delivery_vals(self, line):
        """Build delivery values for each invoice line.

        Used to fill the cac:InvoiceLine/cac:Item node in UBL TR XML export.

        :param line:        An invoice line.
        :return:            A dictionary with delivery information.
        """
        return {
            "incoterm_code": line.move_id.invoice_incoterm_id.code,
            "product_customs_code": line.l10n_tr_gibp_number
            or line.product_id.l10n_tr_gibp_number,
            "shipping_method_code": line.move_id.l10n_tr_shipping_type,
            "delivery_address_vals": {
                "street": line.move_id.partner_id.street,
                "state": line.move_id.partner_id.state_id.with_context(
                    lang="tr_TR"
                ).name,
                "city": line.move_id.partner_id.city,
                "country": line.move_id.partner_id.country_id.with_context(
                    lang="tr_TR"
                ).name,
                "zip": line.move_id.partner_id.zip,
            },
        }

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        """Extend partner tax scheme values to include the Turkish tax office name.

        Adds the tax office name to the `tax_scheme_vals`
        if it exists on the partner.

        :param partner: The partner (customer or supplier).
        :param role: The role in the invoice (e.g. buyer or seller).
        :return: A list of tax scheme dictionaries including the tax office name if applicable.
        """
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        for vals in vals_list:
            if partner.l10n_tr_tax_office_id:
                vals["tax_scheme_vals"].update(
                    {"id": "", "name": partner.l10n_tr_tax_office_id.name}
                )
        return vals_list

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # _export_invoice normally cleans up the xml to remove empty nodes.
        # However, in the TR UBL version, we always want the Shipment with ID empty node, due to it being required.
        # We'll replace the empty value by a dummy one so that the node doesn't get cleaned up and remove its content after the file generation.
        xml, errors = super()._export_invoice(invoice)
        xml_root = etree.fromstring(xml)
        shipment_id_elements = xml_root.findall(
            ".//cac:Shipment/cbc:ID", namespaces=xml_root.nsmap
        )
        for element in shipment_id_elements:
            if element.text == "NO_ID":
                element.text = ""
        return etree.tostring(xml_root, xml_declaration=True, encoding="UTF-8"), errors
