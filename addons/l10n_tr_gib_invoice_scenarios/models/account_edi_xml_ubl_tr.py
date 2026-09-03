from collections import defaultdict

from odoo import api, models
from odoo.exceptions import UserError

from odoo.addons.l10n_tr_nilvera_einvoice_extended.tools.ubl_tr_invoice import TrInvoice


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = "account.edi.xml.ubl.tr"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        # The Nilvera Extended flow is only for out_invoice and out_refund type
        if vals["document_type"] not in {"invoice", "credit_note"}:
            return
        invoice = vals["invoice"]

        if vals["document_type"] == "credit_note":
            document_node.update(
                {
                    "cbc:ProfileID": {"_text": self._get_tr_profile_id(invoice)},
                    "cbc:InvoiceTypeCode": {
                        "_text": "ISTISNA" if invoice.l10n_tr_is_export_invoice else invoice.l10n_tr_gib_invoice_type
                    },
                    "cbc:CreditNoteTypeCode": None,
                }
            )

        if invoice.move_type == "out_refund":
            # For credit notes, we need to add cac:BillingReference (i.e. reference to the original invoice)
            self._l10n_tr_add_billing_reference_node(document_node, vals)

    @api.model
    def _l10n_tr_add_billing_reference_node(self, document_node, vals):
        invoice = vals["invoice"]
        if not invoice.reversed_entry_id and not invoice.ref:
            raise UserError(
                self.env._(
                    "The credit note must be linked to the original invoice, or include the invoice reference in the reference field."
                )
            )
        _, parts = invoice._get_sequence_format_param(invoice.reversed_entry_id.name or invoice.ref)
        prefix, year, number = parts["prefix1"][:3], parts["year"], str(parts["seq"]).zfill(9)
        reverese_entry_id = f"{prefix.upper()}{year}{number}"
        document_node["cac:BillingReference"] = {
            "cac:InvoiceDocumentReference": {
                "cbc:ID": {"_text": reverese_entry_id},
                "cbc:IssueDate": {"_text": invoice.reversed_entry_id.invoice_date or invoice.l10n_tr_original_invoice_date},
                "cbc:DocumentTypeCode": {"_text": "İADE"},
                "cbc:DocumentDescription": {"_text": "İade Edilen Fatura"},
            },
        }

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        if vals["document_type"] == "credit_note":
            return
        super()._add_invoice_payment_means_nodes(document_node, vals)

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        """Adds tax total nodes to a document line.

        For Turkish withholding return invoices TEVKIFATIADE, this method
        delegates to add_withholding_return_document_line_tax_total_nodes.
        Otherwise, it falls back to the default behavior.

        :param line_node: XML node representing the invoice line.
        :param vals: Dictionary containing the invoice data.
        :return: Updated XML line node with tax total information.
        """
        if vals["invoice"].l10n_tr_gib_invoice_type == "TEVKIFATIADE":
            return self._add_withholding_return_document_line_tax_total_nodes(line_node, vals)
        return super()._add_document_line_tax_total_nodes(line_node, vals)

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        """Adds tax total nodes to the invoice document.

        For Turkish withholding return invoices ('TEVKIFATIADE'), this method
        delegates to `_add_withholding_return_document_tax_total_nodes`.
        Otherwise, it uses the default tax total behavior.

        :param document_node: XML node representing the full invoice document.
        :param vals: Dictionary containing the invoice data.
        :return: lxml.etree.Element or similar XML node representing the updated invoice document.

        """
        if vals["invoice"].l10n_tr_gib_invoice_type == "TEVKIFATIADE":
            return self._add_withholding_return_document_tax_total_nodes(document_node, vals)
        return super()._add_invoice_tax_total_nodes(document_node, vals)

    def _add_withholding_return_document_tax_total_nodes(self, document_node, vals):
        tax_subtotals_per_currency = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        for base_line in vals["base_lines"]:
            line = base_line["record"]
            taxes_data = base_line.get("tax_details", {}).get("taxes_data", [])
            total_taxed_amount = sum(tax_line["tax_amount"] for tax_line in taxes_data)

            percent_return = (line.l10n_tr_original_quantity and line.quantity * 100 / line.l10n_tr_original_quantity) or 0
            tax_subtotals_per_currency[line.currency_id][percent_return]["taxable_amount"] += (
                line.l10n_tr_original_tax_without_withholding
            )
            tax_subtotals_per_currency[line.currency_id][percent_return]["tax_amount"] += total_taxed_amount

        tax_totals = []
        for currency_id, subtotal_aggregates in tax_subtotals_per_currency.items():
            currency_name = currency_id.name
            precision = currency_id.decimal_places
            tax_amount = 0
            tax_subtotals = []
            for percent_return, subtotal in subtotal_aggregates.items():
                tax_amount += subtotal["tax_amount"]
                tax_subtotals.append(
                    {
                        "cbc:TaxableAmount": {
                            "_text": self.format_float(
                                subtotal["taxable_amount"],
                                precision,
                            ),
                            "currencyID": currency_name,
                        },
                        "cbc:TaxAmount": {
                            "_text": self.format_float(
                                subtotal["tax_amount"],
                                precision,
                            ),
                            "currencyID": currency_name,
                        },
                        "cbc:Percent": {
                            "_text": percent_return,
                        },
                        "cac:TaxCategory": {
                            "cac:TaxScheme": {
                                "cbc:Name": {
                                    "_text": "Gerçek Usulde KDV",
                                },
                                "cbc:TaxTypeCode": {
                                    "_text": "0015",
                                },
                            },
                        },
                    },
                )
            tax_totals.append(
                {
                    "cbc:TaxAmount": {
                        "_text": self.format_float(tax_amount, precision),
                        "currencyID": currency_name,
                    },
                    "cac:TaxSubtotal": tax_subtotals,
                }
            )

        document_node["cac:TaxTotal"] = tax_totals

    def _add_withholding_return_document_line_tax_total_nodes(self, line_node, vals):
        base_line = vals["base_line"]
        line = base_line["record"]
        currency_name = line.currency_id.name
        precision = line.currency_id.decimal_places
        percent_return = (line.l10n_tr_original_quantity and line.quantity * 100 / line.l10n_tr_original_quantity) or 0

        taxes_data = base_line.get("tax_details", {}).get("taxes_data", [])
        total_taxed_amount = sum(tax_line["tax_amount"] for tax_line in taxes_data)
        line_node["cac:TaxTotal"] = [
            {
                "cbc:TaxAmount": {
                    "_text": self.format_float(total_taxed_amount, precision),
                    "currencyID": currency_name,
                },
                "cac:TaxSubtotal": {
                    "cbc:TaxableAmount": {
                        "_text": self.format_float(
                            line.l10n_tr_original_tax_without_withholding,
                            precision,
                        ),
                        "currencyID": currency_name,
                    },
                    "cbc:TaxAmount": {
                        "_text": self.format_float(
                            total_taxed_amount,
                            precision,
                        ),
                        "currencyID": currency_name,
                    },
                    "cbc:Percent": {
                        "_text": percent_return,
                    },
                    "cac:TaxCategory": {
                        "cac:TaxScheme": {
                            "cbc:Name": {
                                "_text": "Gerçek Usulde KDV",
                            },
                            "cbc:TaxTypeCode": {
                                "_text": "0015",
                            },
                        },
                    },
                },
            },
        ]

    def _get_document_template(self, vals):
        """Determines the document template to use based on the provided values.

        If the document is a Turkish credit note (CustomizationID 'TR1.2' and document_type 'credit_note'),
        it returns the `TrInvoice` template. Otherwise, it falls back to the default implementation.

        :param vals: Dictionary containing document data, including 'document_node' and 'document_type'.
        :return: Document template class to be used for generating the document.
        """
        if vals["document_node"]["cbc:CustomizationID"]["_text"] == "TR1.2" and vals["document_type"] == "credit_note":
            return TrInvoice
        return super()._get_document_template(vals)

    def _get_document_nsmap(self, vals):
        res = super()._get_document_nsmap(vals)
        if vals["document_type"] == "credit_note":
            res[None] = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
        return res

    def _get_tags_for_document_type(self, vals):
        res = super()._get_tags_for_document_type(vals)
        if vals["document_type"] == "credit_note":
            res.update(
                {
                    "document_type_code": "cbc:InvoiceTypeCode",
                    "document_line": "cac:InvoiceLine",
                    "line_quantity": "cbc:InvoicedQuantity",
                }
            )
        return res

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        # EXTENDS account.edi.xml.ubl_20
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)

        scenario = self._find_value(".//cbc:ProfileID", tree)
        if scenario not in {key for key, _ in self.env["account.move"]._fields["l10n_tr_gib_invoice_scenario"].selection}:
            scenario = False
        invoice_type = self._find_value(".//cbc:InvoiceTypeCode", tree)
        if invoice_type not in {key for key, _ in self.env["account.move"]._fields["l10n_tr_gib_invoice_type"].selection}:
            invoice_type = False

        invoice.write(
            {
                "l10n_tr_nilvera_uuid": self._find_value("./cbc:UUID", tree),
                "l10n_tr_gib_invoice_scenario": scenario,
                "l10n_tr_gib_invoice_type": invoice_type,
            }
        )

        if scenario == "TICARIFATURA" and invoice.move_type in {"in_invoice", "out_invoice"}:
            try:
                # Don't want to block the import in case status retrieval fails
                invoice.l10n_tr_action_fetch_ticarifatura_response()
            except UserError as e:
                logs.append(self.env._("Failed to fetch TICARIFATURA response: %s", str(e)))

        return logs
