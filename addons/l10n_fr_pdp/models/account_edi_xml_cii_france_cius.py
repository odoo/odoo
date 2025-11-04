from odoo import models


class AccountEdiXmlCiiFranceCius(models.AbstractModel):
    _name = 'account.edi.xml.cii_france_cius'
    _inherit = 'account.edi.xml.cii'
    _description = 'UN/CEFACT CII France CIUS (EN16931)'

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        vals['document_context_id'] = 'urn:cen.eu:en16931:2017'
        return vals
