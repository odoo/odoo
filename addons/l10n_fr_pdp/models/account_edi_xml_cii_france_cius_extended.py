from odoo import models


class AccountEdiXmlCiiFranceCiusExtended(models.AbstractModel):

    _name = "account.edi.xml.cii_france_cius_extended"
    _inherit = "account.edi.xml.cii_france_cius"
    _description = "UN/CEFACT CII France CIUS (EN16931) Extended CTC FR"

    template_to_render = "l10n_fr_pdp.cii_france_extended_invoice"

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        vals['document_context_id'] = 'urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended'
        return vals
