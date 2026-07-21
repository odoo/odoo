from odoo import models


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"

    def _can_export_selfbilling(self):
        # At the moment, self-billing is only supported for BIS3.
        return self._name == 'account.edi.xml.ubl_bis3'

    def _add_invoice_config_vals(self, vals):
        super()._add_invoice_config_vals(vals)
        invoice = vals['invoice']
        vals['process_type'] = 'selfbilling' if invoice.is_purchase_document() and self._can_export_selfbilling() else 'billing'
