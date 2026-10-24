
from odoo import models


class AccountEdiXmlUBLNL(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_nl'

    def _can_export_selfbilling(self):
        return super()._can_export_selfbilling() or self._name == ('account.edi.xml.ubl_nl')

    def _ubl_add_profile_id_node(self, vals):
        super()._ubl_add_profile_id_node(vals)
        # NLCIUS doesn't need specific ProfileID for self-billing
        vals['document_node']['cbc:ProfileID']['_text'] = 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'
