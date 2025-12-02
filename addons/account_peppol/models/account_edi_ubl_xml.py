from odoo import models


class AccountEdiXmlUbl_20(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _add_invoice_config_vals(self, vals):
        """
        When generating the XML on behalf of the parent peppol company,
        use the parent company details on the XML.
        """
        super()._add_invoice_config_vals(vals)
        invoice = vals['invoice']
        company = invoice.company_id

        if parent_peppol_company := company.peppol_parent_company_id:
            vals['supplier'] = parent_peppol_company.partner_id.commercial_partner_id
