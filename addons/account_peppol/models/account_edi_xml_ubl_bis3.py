from odoo import models


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        constraints = super()._invoice_constraints_peppol_en16931_ubl(invoice, vals)
        # A BIS3 file handed to an accountant for a B2C sale carries no endpoint and is
        # still valid; only a document travelling on Peppol needs both addresses.
        if not self.env.context.get("from_peppol"):
            return constraints

        document_node = vals["document_node"]
        customer_party = document_node["cac:AccountingCustomerParty"]["cac:Party"]
        if not customer_party["cbc:EndpointID"]["_text"]:
            constraints["ubl_peppol_en16931-r010"] = self.env._(
                "[PEPPOL-EN16931-R010] An electronic address (EAS) must be provided on the customer '%s'.",
                vals["customer"].display_name,
            )
        supplier_party = document_node["cac:AccountingSupplierParty"]["cac:Party"]
        if not supplier_party["cbc:EndpointID"]["_text"]:
            constraints["ubl_peppol_en16931-r020"] = self.env._(
                "[PEPPOL-EN16931-R020] An electronic address (EAS) must be provided on the company '%s'.",
                vals["supplier"].display_name,
            )
        return constraints
