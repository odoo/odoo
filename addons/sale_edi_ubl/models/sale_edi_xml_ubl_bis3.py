from lxml import etree

from odoo import Command, _, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import html2plaintext
from odoo.tools.xml_utils import dict_to_xml

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt
from odoo.addons.account_edi_ubl_cii.tools import Order

_debug = DebugLog(__name__)


class SaleEdiXmlUbl_Bis3(models.AbstractModel):
    _name = "sale.edi.xml.ubl_bis3"
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "Sale BIS Ordering 3.5"

    def _export_order(self, sale_order):
        vals = {"sale_order": sale_order}
        document_node = self._get_sale_order_node(vals)
        xml_content = dict_to_xml(
            document_node, template=Order, nsmap=self._get_document_nsmap(vals)
        )
        _debug.pipeline("edi_order_exported", order=sale_order)
        return etree.tostring(xml_content, xml_declaration=True, encoding="UTF-8")

    def _get_sale_order_node(self, vals):
        self._add_sale_order_config_vals(vals)
        self._add_sale_order_base_lines_vals(vals)
        self._add_sale_order_currency_vals(vals)
        self._add_sale_order_tax_grouping_function_vals(vals)
        self._setup_base_lines(vals)
        self._add_sale_order_monetary_totals_vals(vals)

        document_node = {}
        self._add_sale_order_header_nodes(document_node, vals)
        self._add_sale_order_buyer_customer_party_nodes(document_node, vals)
        self._add_sale_order_seller_supplier_party_nodes(document_node, vals)
        self._add_sale_order_delivery_nodes(document_node, vals)
        self._add_sale_order_payment_terms_nodes(document_node, vals)
        self._add_sale_order_line_nodes(document_node, vals)
        self._add_sale_order_allowance_charge_nodes(document_node, vals)
        self._add_sale_order_tax_total_nodes(document_node, vals)
        self._add_sale_order_monetary_total_nodes(document_node, vals)
        return document_node

    def _add_sale_order_config_vals(self, vals):
        sale_order = vals["sale_order"]
        supplier = sale_order.company_id.partner_id.commercial_partner_id
        customer = sale_order.partner_id

        customer_delivery_address = customer.child_ids.filtered(
            lambda child: child.type == "delivery"
        )
        partner_shipping = (
            sale_order.partner_shipping_id
            or (customer_delivery_address and customer_delivery_address[0])
            or customer
        )
        vals.update(
            {
                "document_type": "order",
                "supplier": supplier,
                "customer": customer,
                "partner_shipping": partner_shipping,
                "company": sale_order.company_id,
                "currency_id": sale_order.currency_id,
                "company_currency_id": sale_order.company_id.currency_id,
                "use_company_currency": False,
                "fixed_taxes_as_allowance_charges": True,
            }
        )

    def _add_sale_order_base_lines_vals(self, vals):
        sale_order = vals["sale_order"]
        AccountTax = self.env["account.tax"]

        base_lines = [
            line._prepare_base_line_for_taxes_computation()
            for line in sale_order.line_ids.filtered(lambda line: not line.display_type)
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, sale_order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, sale_order.company_id)

        vals["base_lines"] = base_lines

    def _add_sale_order_currency_vals(self, vals):
        self._add_document_currency_vals(vals)

    def _add_sale_order_tax_grouping_function_vals(self, vals):
        self._add_document_tax_grouping_function_vals(vals)

    def _add_sale_order_monetary_totals_vals(self, vals):
        self._add_document_monetary_total_vals(vals)

    def _add_sale_order_header_nodes(self, document_node, vals):
        sale_order = vals["sale_order"]
        document_node.update(
            {
                "cbc:CustomizationID": {
                    "_text": "urn:fdc:peppol.eu:poacc:trns:order:3"
                },
                "cbc:ProfileID": {"_text": "urn:fdc:peppol.eu:poacc:bis:ordering:3"},
                "cbc:ID": {"_text": sale_order.name},
                "cbc:IssueDate": {"_text": sale_order.create_date.date()},
                "cbc:OrderTypeCode": {"_text": "220"},
                "cbc:Note": {"_text": html2plaintext(sale_order.notes)}
                if sale_order.notes
                else None,
                "cbc:DocumentCurrencyCode": {"_text": vals["currency_name"]},
                "cac:ValidityPeriod": {
                    "cbc:EndDate": {"_text": sale_order.date_validity},
                },
                "cac:OriginatorDocumentReference": {
                    "cbc:ID": {"_text": sale_order.client_order_ref}
                },
            }
        )

    def _add_sale_order_buyer_customer_party_nodes(self, document_node, vals):
        document_node["cac:BuyerCustomerParty"] = {
            "cac:Party": self._get_party_node(
                {**vals, "partner": vals["customer"], "role": "customer"}
            )
        }

    def _add_sale_order_seller_supplier_party_nodes(self, document_node, vals):
        document_node["cac:SellerSupplierParty"] = {
            "cac:Party": self._get_party_node(
                {**vals, "partner": vals["supplier"], "role": "supplier"}
            )
        }

    def _add_sale_order_delivery_nodes(self, document_node, vals):
        document_node["cac:Delivery"] = {
            "cac:DeliveryParty": self._get_party_node(
                {**vals, "partner": vals["partner_shipping"], "role": "delivery"}
            )
        }

    def _add_sale_order_payment_terms_nodes(self, document_node, vals):
        sale_order = vals["sale_order"]
        if sale_order.payment_term_id:
            document_node["cac:PaymentTerms"] = {
                "cbc:Note": {"_text": sale_order.payment_term_id.name}
            }

    def _add_sale_order_allowance_charge_nodes(self, document_node, vals):
        ubl_values = vals["_ubl_values"]
        document_node["cac:AllowanceCharge"] = [
            self._ubl_get_allowance_charge_early_payment(vals, early_payment_values)
            for early_payment_values in ubl_values[
                "allowance_charges_early_payment_currency"
            ]
        ]

    def _add_sale_order_tax_total_nodes(self, document_node, vals):
        sub_vals = {
            **vals,
            "document_node": document_node,
            "currency": vals["currency_id"],
        }
        self._ubl_add_tax_totals_nodes(sub_vals)

    def _add_sale_order_monetary_total_nodes(self, document_node, vals):
        ubl_values = vals["_ubl_values"]
        sale_order = vals["sale_order"]

        line_extension_amount = sum(
            line_node["cac:LineItem"]["cbc:LineExtensionAmount"]["_text"]
            for line_node in document_node["cac:OrderLine"]
        )
        tax_amount = sum(
            tax_total["cbc:TaxAmount"]["_text"]
            for tax_total in document_node["cac:TaxTotal"]
            if tax_total["cbc:TaxAmount"]["currencyID"] == vals["currency_id"].name
        )
        total_allowance = sum(
            allowance_charge["cbc:Amount"]["_text"]
            for allowance_charge in document_node["cac:AllowanceCharge"]
            if allowance_charge["cbc:ChargeIndicator"]["_text"] == "false"
        )
        total_charge = sum(
            allowance_charge["cbc:Amount"]["_text"]
            for allowance_charge in document_node["cac:AllowanceCharge"]
            if allowance_charge["cbc:ChargeIndicator"]["_text"] == "true"
        )
        payable_rounding_amount = ubl_values["payable_rounding_amount_currency"]

        document_node["cac:AnticipatedMonetaryTotal"] = {
            "cbc:LineExtensionAmount": {
                "_text": FloatFmt(line_extension_amount, min_dp=vals["currency_dp"]),
                "currencyID": vals["currency_name"],
            },
            "cbc:TaxExclusiveAmount": {
                "_text": FloatFmt(line_extension_amount, min_dp=vals["currency_dp"]),
                "currencyID": vals["currency_name"],
            },
            "cbc:TaxInclusiveAmount": {
                "_text": FloatFmt(
                    line_extension_amount + tax_amount, min_dp=vals["currency_dp"]
                ),
                "currencyID": vals["currency_name"],
            },
            "cbc:AllowanceTotalAmount": {
                "_text": FloatFmt(total_allowance, min_dp=vals["currency_dp"]),
                "currencyID": vals["currency_name"],
            }
            if total_allowance
            else None,
            "cbc:ChargeTotalAmount": {
                "_text": FloatFmt(total_charge, min_dp=vals["currency_dp"]),
                "currencyID": vals["currency_name"],
            }
            if total_charge
            else None,
            "cbc:PrepaidAmount": {
                "_text": FloatFmt(sale_order.amount_paid, min_dp=vals["currency_dp"]),
                "currencyID": vals["currency_name"],
            },
            "cbc:PayableRoundingAmount": {
                "_text": FloatFmt(payable_rounding_amount, min_dp=vals["currency_dp"]),
                "currencyID": vals["currency_name"],
            }
            if payable_rounding_amount
            else None,
            "cbc:PayableAmount": {
                "_text": FloatFmt(
                    sale_order.amount_total - sale_order.amount_paid,
                    min_dp=vals["currency_dp"],
                ),
                "currencyID": vals["currency_name"],
            },
        }

    def _add_sale_order_line_nodes(self, document_node, vals):
        document_node["cac:OrderLine"] = order_line_nodes = []

        for line_idx, base_line in enumerate(vals["base_lines"], start=1):
            line_vals = {
                **vals,
                "line_idx": line_idx,
                "base_line": base_line,
            }
            self._add_sale_order_line_vals(line_vals)

            line_node = {}
            self._add_sale_order_line_id_nodes(line_node, line_vals)
            self._add_sale_order_line_allowance_charge_nodes(line_node, line_vals)
            self._add_sale_order_line_amount_nodes(line_node, line_vals)
            self._add_sale_order_line_item_nodes(line_node, line_vals)
            self._add_sale_order_line_price_nodes(line_node, line_vals)

            order_line_nodes.append(
                {
                    "cac:LineItem": line_node,
                }
            )

    def _add_sale_order_line_vals(self, vals):
        self._add_document_line_vals(vals)

    def _add_sale_order_line_id_nodes(self, line_node, vals):
        self._add_document_line_id_nodes(line_node, vals)

    def _add_sale_order_line_amount_nodes(self, line_node, vals):
        sub_vals = {
            **vals,
            "line_node": line_node,
            "line_vals": {
                "base_line": vals["base_line"],
            },
        }
        self._ubl_add_line_quantity_node(sub_vals)
        self._ubl_add_line_extension_amount_node(sub_vals)

    def _add_sale_order_line_allowance_charge_nodes(self, line_node, vals):
        sub_vals = {
            **vals,
            "line_node": line_node,
            "line_vals": {
                "base_line": vals["base_line"],
            },
        }
        self._ubl_add_line_allowance_charge_nodes(sub_vals)

        self._ubl_add_line_allowance_charge_nodes_for_discount(sub_vals)

        self._ubl_add_line_allowance_charge_nodes_for_recycling_contribution_taxes(
            sub_vals
        )

        self._ubl_add_line_allowance_charge_nodes_for_excise_taxes(sub_vals)

    def _add_sale_order_line_item_nodes(self, line_node, vals):
        sub_vals = {
            **vals,
            "line_node": line_node,
            "line_vals": {
                "base_line": vals["base_line"],
            },
        }
        self._ubl_add_line_item_node(sub_vals)

    def _add_sale_order_line_price_nodes(self, line_node, vals):
        base_line = vals["base_line"]
        ubl_values = base_line["_ubl_values"]

        line_node["cac:Price"] = {
            "cbc:PriceAmount": {
                "_text": FloatFmt(
                    ubl_values["price_amount_currency"], min_dp=1, max_dp=6
                ),
                "currencyID": vals["currency_name"],
            },
        }

    def _ubl_get_line_allowance_charge_discount_node(self, vals, discount_values):
        discount_node = super()._ubl_get_line_allowance_charge_discount_node(
            vals, discount_values
        )
        discount_node["cbc:AllowanceChargeReason"] = None
        discount_node["cbc:MultiplierFactorNumeric"] = None
        discount_node["cbc:BaseAmount"] = None
        return discount_node

    def _prepare_order_vals(self, order, tree):
        order_vals, logs = super()._prepare_order_vals(order, tree)
        order_vals.pop("notes", False)
        partner, partner_logs = self._import_partner(
            order.company_id,
            **self._prepare_partner_import_params(tree, "BuyerCustomer"),
        )
        if partner:
            order_vals["partner_id"] = partner.id
        order_vals["client_order_ref"] = tree.findtext("./{*}ID")
        order_vals["origin"] = tree.findtext("./{*}QuotationDocumentReference/{*}ID")

        delivery_partner, delivery_logs = self._import_partner(
            order.company_id,
            **self._prepare_partner_import_params(tree, "Delivery"),
        )
        if delivery_partner:
            order_vals["partner_shipping_id"] = delivery_partner.id

        allowance_charges_line_vals, allowance_charges_logs = (
            self._import_document_allowance_charges(tree, order, "sale")
        )
        lines_vals, line_logs = self._import_lines(
            order,
            tree,
            "./{*}OrderLine/{*}LineItem",
            document_type="order",
            tax_type="sale",
        )
        for line in lines_vals:
            line["product_qty"] = line.pop("quantity")
            line.pop("deferred_start_date", False)
            line.pop("deferred_end_date", False)
            if not line.get("product_id"):
                _debug.logic("edi_product_unmatched", order=order, name=line["name"])
                line_logs.append(
                    _(
                        "Could not retrieve the product named: %(name)s",
                        name=line["name"],
                    )
                )
            if line.get("discount"):
                line.pop("discount")
        lines_vals += allowance_charges_line_vals

        order_vals["line_ids"] = [Command.create(line_vals) for line_vals in lines_vals]
        logs += partner_logs + delivery_logs + line_logs + allowance_charges_logs
        _debug.pipeline(
            "edi_order_parsed",
            order=order,
            lines=len(lines_vals),
            logs=len(logs),
            partner=partner,
        )

        return order_vals, logs

    def _import_order_ubl(self, order, file_data, new):
        res = super()._import_order_ubl(order, file_data, new)
        _debug.pipeline("edi_prices_recomputed", order=order, lines=order.line_ids)
        order.line_ids.filtered("product_id").with_context(
            force_price_recomputation=True
        )._compute_price_and_discount()

        return res

    def _get_product_xpaths(self):
        return {
            **super()._get_product_xpaths(),
            "variant_barcode": "./cac:Item/cac:StandardItemIdentification/cbc:ExtendedID",
            "variant_default_code": "./cac:Item/cac:SellersItemIdentification/cbc:ExtendedID",
        }
