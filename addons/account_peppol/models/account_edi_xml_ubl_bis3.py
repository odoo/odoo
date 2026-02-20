from odoo import _, models


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        # Some constraints are specific to Peppol because the xml file might be used in B2C operations
        # without Peppol but to be given to the accountant to import the invoice in another accounting
        # software.
        constraints = super()._invoice_constraints_peppol_en16931_ubl(invoice, vals)

        if self.env.context.get('from_peppol'):
            # [PEPPOL-EN16931-R010]
            if not vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cbc:EndpointID']['_text']:
                constraints['ubl_peppol_en16931-r010'] = _(
                    "[PEPPOL-EN16931-R010] An electronic address (EAS) must be provided on the customer '%s'.",
                    vals['customer'].display_name,
                )

            # [PEPPOL-EN16931-R020]
            if not vals['document_node']['cac:AccountingSupplierParty']['cac:Party']['cbc:EndpointID']['_text']:
                constraints['ubl_peppol_en16931-r020'] = _(
                    "[PEPPOL-EN16931-R020] An electronic address (EAS) must be provided on the company '%s'.",
                    vals['supplier'].display_name,
                )

        return constraints
