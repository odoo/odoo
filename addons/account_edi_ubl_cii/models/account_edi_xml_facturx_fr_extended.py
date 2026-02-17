from lxml import etree
from odoo import models


class AccountEdiXmlFacturxFrExtended(models.AbstractModel):
    _name = "account.edi.xml.facturx_fr_extended"
    _inherit = "account.edi.xml.cii_fr_extended"
    _description = "Factur-X France (Extended)"

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_facturx_extended.xml"

    def _get_document_context_id(self):
        return "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"

    def _patch_facturx_pdfa3_metadata(self, metadata_content, xml_filename):
        """Patch the Factur-X PDF/A-3 XMP metadata."""

        ns = {'fx': 'urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#'}
        tree = etree.fromstring(metadata_content.encode('utf-8'))

        conformance_node = tree.find('.//fx:ConformanceLevel', namespaces=ns)
        if conformance_node is not None:
            conformance_node.text = "EXTENDED"

        filename_node = tree.find('.//fx:DocumentFileName', namespaces=ns)
        if filename_node is not None:
            filename_node.text = xml_filename

        return etree.tostring(tree, encoding='unicode')
