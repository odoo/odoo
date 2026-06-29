from odoo import models
from odoo.tools import cleanup_xml_node
from lxml import etree


class AccountEdiXmlCiiFranceCius(models.AbstractModel):

    _name = "account.edi.xml.cii_france_cius"
    _inherit = "account.edi.xml.cii"
    _description = "UN/CEFACT CII France CIUS (EN16931)"

    template_to_render = "l10n_fr_pdp.cii_france_cius_invoice"

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        vals['document_context_id'] = "urn:cen.eu:en16931:2017"
        return vals

    def _export_invoice(self, invoice):
        vals = self._export_invoice_vals(invoice.with_context(lang=invoice.partner_id.lang))
        errors = [constraint for constraint in self._export_invoice_constraints(invoice, vals).values() if constraint]
        xml_content = self.env['ir.qweb']._render(self.template_to_render, vals)
        return etree.tostring(cleanup_xml_node(xml_content), xml_declaration=True, encoding='UTF-8'), set(errors)
