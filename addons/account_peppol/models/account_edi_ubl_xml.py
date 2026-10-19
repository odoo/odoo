from odoo import models


class AccountEdiXmlUBL(models.AbstractModel):
    _inherit = 'account.edi.ubl'

    def _ubl_add_values_supplier(self, vals, supplier):
        """
        When generating the XML on behalf of the parent peppol company,
        use the parent company details on the XML.
        """
        super()._ubl_add_values_supplier(vals, supplier)

        company = vals['company']
        if parent_peppol_company := company.peppol_parent_company_id:
            vals['supplier'] = parent_peppol_company.partner_id.commercial_partner_id
