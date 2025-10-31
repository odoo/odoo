from lxml import etree

from odoo import api, models


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
                },
            ]

            # Update invoice values
            vals["vals"].update(
                {
                    "document_type_code": "ISTISNA",
                    "buyer_customer_party_vals": buyer_customer_party_vals,
                    "accounting_customer_party_vals": self._get_ministry_vals(),
                },
            )

            # Set invoice type template
            vals["InvoiceType_template"] = "l10n_tr_nilvera_einvoice_extended.ubl_tr_export_InvoiceType"
        elif invoice.l10n_tr_gib_invoice_type == "TEVKIFAT":
            vals["vals"].update(
                {
                    "withholding_tax_total_vals_list": self._get_tr_tax_totals(
                        invoice,
                        vals["taxes_vals"],
                        withholding=True,
                    ),
                },
            )
        vals.update(
            {
                "InvoiceLineType_template": "l10n_tr_nilvera_einvoice_extended.ubl_tr_InvoiceLineType",
                "InvoiceLineDelivery_template": "l10n_tr_nilvera_einvoice_extended.ubl_tr_LineDelivery",
            },
        )

        return vals

    @api.model
    def _get_ministry_vals(self):
        """Return the fixed ministry (party) information required for TR E-invoicing.

        This method provides identification, address, tax, and naming
        details of the Turkish Ministry of Customs and Trade.

        :return: dict containing the structured ministry/party values.
        """
        return {
            "party_vals": {
                "party_identification_vals": [
                    {
                        "id_attrs": {"schemeID": "VKN"},
                        "id": "1460415308",
                    },
                ],
                "postal_address_vals": {
                    "city_subdivision_name ": "Ulus",
                    "city_name": "Ankara",
                    "country_vals": {
                        "name": "Türkiye",
                    },
                },
                "party_name_vals": [
                    {"name": "Gümrük ve Ticaret Bakanlığı Gümrükler Genel Müdürlüğü- Bilgi İşlem Dairesi Başkanlığı"},
                ],
                "party_tax_scheme_vals": [{"tax_scheme_vals": {"name": "Ulus"}}],
            },
        }

    @api.model
    def _get_tr_profile_id(self, invoice):
        """Determine the TR profile ID for the given invoice.

        Logic:
        - If the customer is an e-invoice user and the invoice has a
          l10n_tr_gib_invoice_scenario, return that scenario.
        - If the invoice is marked as an export invoice, return "IHRACAT".
        - Otherwise:
            • Return "TEMELFATURA" if the customer is an e-invoice user.
            • Return "EARSIVFATURA" for e-archive invoices.

        :param invoice: account.move record (the invoice).
        :return: str, TR profile ID to be used in E-invoicing.
        """
        if (is_einvoice := invoice.l10n_tr_nilvera_customer_status == "einvoice") and invoice.l10n_tr_gib_invoice_scenario:
            return invoice.l10n_tr_gib_invoice_scenario
        if invoice.l10n_tr_is_export_invoice:
            return "IHRACAT"
        return "TEMELFATURA" if is_einvoice else "EARSIVFATURA"

    def _get_tax_category_list(self, customer, supplier, taxes):
        """Extend tax category list to include Turkish withholding tax codes.

        Filters out withholding taxes from the main list and appends them separately
        with Turkish-specific tax scheme values.

        :param customer: The partner receiving the invoice.
        :param supplier: The partner issuing the invoice.
        :param taxes: Recordset of taxes.
        :return: A list of tax category values.
        """
        tr_withholding_taxes = taxes.filtered(lambda t: t.l10n_tr_tax_withholding_code_id)
        res = super()._get_tax_category_list(customer, supplier, taxes - tr_withholding_taxes)
        for tax in tr_withholding_taxes:
            res.append(
                {
                    "id": tax.l10n_tr_tax_withholding_code_id.code,
                    "percent": tax.l10n_tr_tax_withholding_code_id.percentage,
                    "tax_scheme_vals": {
                        "name": tax.l10n_tr_tax_withholding_code_id.with_context(lang="tr_TR").name,
                        "tax_type_code": tax.l10n_tr_tax_withholding_code_id.code,
                    },
                },
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
        grouping_key = super()._get_tax_grouping_key(base_line, tax_data)
        invoice = base_line["record"].move_id
        tax = tax_data["tax"]
        grouping_key["_tax_category_vals_"]["l10n_tr_tax_exempted"] = tax.l10n_tr_tax_withholding_code_id.id
        # Add category values to the category values to the tax scheme dictionary's
        # grouping keys so it can be later used in _get_tax_category_list
        if invoice.l10n_tr_gib_invoice_type == "TEVKIFAT" and tax.l10n_tr_tax_withholding_code_id:
            grouping_key["tax_category_id"] = tax.l10n_tr_tax_withholding_code_id.id
            grouping_key["_tax_category_vals_"]["id"] = tax.l10n_tr_tax_withholding_code_id.code
            grouping_key["_tax_category_vals_"]["percent_withheld"] = tax.l10n_tr_tax_withholding_code_id.percentage
            grouping_key["_tax_category_vals_"]["tax_scheme_vals"]["name"] = tax.l10n_tr_tax_withholding_code_id.with_context(lang="tr_TR").name
            grouping_key["_tax_category_vals_"]["tax_scheme_vals"]["tax_type_code"] = tax.l10n_tr_tax_withholding_code_id.code
        return grouping_key

    @api.model
    def _get_tr_tax_totals(self, invoice, taxes_vals, withholding):
        """Build Turkish UBL-compliant tax totals for e-Invoice Withholding Scenario Only.

        Filters and structures tax subtotal values based on whether the invoice
        includes withholding taxes. Ensures proper formatting of tax categories
        for UBL export.

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
            exempted = key.get("_tax_category_vals_", {}).get("l10n_tr_tax_exempted")
            return exempted if withholding else not exempted

        def get_withholding_taxable_amount():
            return sum(v["tax_amount"] for k, v in taxes_vals["tax_details"].items() if not filter_tax_details(k))

        def get_withholding_tax_total(subtotals):
            return sum(subtotal["tax_amount"] for subtotal in subtotals)

        tax_totals_vals = {
            "currency": invoice.currency_id,
            "currency_dp": self._get_currency_decimal_places(invoice.currency_id),
            "tax_subtotal_vals": [],
        }
        # UBL_TR: Filter tax lines based on exemption reason:
        # - If withholding → include only tax lines with an exemption reason
        # - If not withholding → include only tax lines without an exemption reason
        filtered_tax_details = {k: v for k, v in taxes_vals["tax_details"].items() if filter_tax_details(k)}
        for vals in filtered_tax_details.values():
            # UBL_TR: Prepare tax subtotal values
            # - Copy tax category data and sanitize it for export (remove ID and percent)
            # - For withholding taxes, compute and attach the withholding percentage as an integer
            tax_category_vals = vals.get("_tax_category_vals_", {}).copy()
            subtotal_percent = int(tax_category_vals.get("percent_withheld", 0) * 100)

            tax_category_vals.update({
                "id": False,
                "percent": False,
            })

            tax_totals_vals["tax_subtotal_vals"].append(
                {
                    "currency": invoice.currency_id,
                    "currency_dp": self._get_currency_decimal_places(invoice.currency_id),
                    "taxable_amount": get_withholding_taxable_amount() if withholding else vals.get("base_amount_currency"),
                    "tax_amount": abs(vals.get("tax_amount_currency")),
                    "tax_category_vals": tax_category_vals,
                    "percent": subtotal_percent if withholding else vals.get("_tax_category_vals_", {}).get("percent"),
                },
            )

        tax_totals_vals["tax_amount"] = (
            get_withholding_tax_total(tax_totals_vals["tax_subtotal_vals"])
            if withholding
            else taxes_vals["tax_amount_currency"]
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
            return self._get_tr_tax_totals(invoice, taxes_vals, withholding=False)

        tax_totals_vals = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        tax_invoice_exemption = invoice.l10n_tr_exemption_code_id
        if self.env.context.get("skip_tr_code") or not tax_invoice_exemption:
            return tax_totals_vals

        for vals in tax_totals_vals:
            for subtotal_vals in vals.get("tax_subtotal_vals", []):
                # since tax_category_vals is mutable, we need to deep copy its value to make sure it is unique
                subtotal_vals["tax_category_vals"] = subtotal_vals["tax_category_vals"].copy() if "tax_category_vals" in subtotal_vals else {}
                subtotal_vals["tax_category_vals"]["tax_exemption_reason_code"] = tax_invoice_exemption.code
                subtotal_vals["tax_category_vals"]["tax_exemption_reason"] = tax_invoice_exemption.with_context(lang="tr_TR").name
        return tax_totals_vals

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        return super(AccountEdiXmlUblTr, self.with_context(skip_tr_code=True))._get_invoice_line_tax_totals_vals_list(line, taxes_vals)

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
            vals['withholding_tax_total_vals_list'] = self._get_tr_tax_totals(line.move_id, taxes_vals, withholding=True)
        return vals

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_invoice_monetary_total_vals(invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount)
        # UBL TR: If the Invoice Type is IHRACKAYITLI (Registered for Export), then the cbc:PayableAmount node
        # should have tax exclusive amount instead of tax inclusive amount.
        if invoice.l10n_tr_gib_invoice_type == 'IHRACKAYITLI':
            vals["payable_amount"] = vals["tax_exclusive_amount"]
        return vals

    @api.model
    def _get_invoice_line_delivery_vals(self, line):
        """Build delivery values for each invoice line.

        cac:InvoiceLine/cac:Item node in UBL TR XML export, the ID
        node is required to be present inside the shipmemnt delivery
        block before GoodsItem node.

        :param line: An invoice line.
        :return: A dictionary with delivery information.
        """
        return {
            "id": "NO_ID",
            "incoterm_code": line.move_id.invoice_incoterm_id.code,
            "product_customs_code": line.l10n_tr_ctsp_number or line.product_id.l10n_tr_ctsp_number,
            "shipping_method_code": line.move_id.l10n_tr_shipping_type,
            "delivery_address_vals": {
                "street": line.move_id.partner_id.street,
                "state": line.move_id.partner_id.state_id.with_context(lang="tr_TR").name,
                "city": line.move_id.partner_id.city,
                "country": line.move_id.partner_id.country_id.with_context(lang="tr_TR").name,
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
                vals["tax_scheme_vals"].update({"id": "", "name": partner.l10n_tr_tax_office_id.name})
        return vals_list

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # _export_invoice normally cleans up the xml to remove empty nodes.
        # However, in the TR UBL version, we always want the Shipment with ID empty node, due to it being required.
        # We'll replace the empty value by a dummy one so that the node doesn't get cleaned up and remove its content after the file generation.
        xml, errors = super()._export_invoice(invoice)
        xml_root = etree.fromstring(xml)
        shipment_id_elements = xml_root.findall(".//cac:Shipment/cbc:ID", namespaces=xml_root.nsmap)
        for element in shipment_id_elements:
            if element.text == "NO_ID":
                element.text = ""
        return etree.tostring(xml_root, xml_declaration=True, encoding="UTF-8"), errors
