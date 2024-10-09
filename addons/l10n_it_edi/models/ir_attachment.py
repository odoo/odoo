# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import deepcopy
from lxml import etree

from odoo import models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _decode_edi_xml(self, filename, content):
        """ Italian FatturaPA files may have one file per multiple invoices.
            If we detect such a file, we decompose it into a sequence of attachment entries
            by branching the XML tree into sections and treating them as separate attachments.
            :returns:     A list of dictionaries representing attachments.
        """
        to_process = []
        for file_data in super()._decode_edi_xml(filename, content):
            if (
                file_data['type'] == 'xml'
                and len(xml_tree := file_data.get("xml_tree"))
                and etree.QName(xml_tree).localname == 'FatturaElettronica'
            ):
                to_process.append(self._l10n_it_edi_split(file_data))
            else:
                to_process.append(file_data)
        return to_process

    def _l10n_it_edi_split(self, file_data):
        # The file's XML tree represents a collection of invoices.
        # We branch it into one section per invoice and handle them separately.
        xml_tree = file_data['xml_tree']
        xml_tree_parts = []
        bodies = xml_tree.findall(".//FatturaElettronicaBody")
        if len(bodies) > 1:
            parent = bodies[0].getparent()
            # Remove all bodies
            for body in bodies:
                parent.remove(body)
            # Add one at a time and create tree copies
            for body in bodies:
                parent.append(body)
                xml_tree_part = deepcopy(xml_tree)
                xml_tree_parts.append({'xml_tree': xml_tree_part})
                parent.remove(body)
        return {
            **file_data,
            'disable_prediction': True,
            'parts': xml_tree_parts,
        }

    def _decode_edi_binary(self, filename, content):
        """ Italian FatturaPA invoices, either coming from the Tax Agency SdICoop webservices
            or manually uploaded by the user, are modeled as XML files.
            They can be binary CADES signed .xml.p7m files, which are XML files
            enveloped in an ASN1 formatted binary structure.
        """
        to_process = []
        to_process_old = super()._decode_edi_binary(filename, content)
        for file_data in to_process_old:
            filename = file_data['filename']
            attachment = file_data['attachment']
            mimetype = attachment.mimetype
            parts = [part.lower() for part in filename.split('.')]
            if 'p7m' in parts or 'application/pkcs7-mime' in mimetype:
                # Remove the CADES signature and handle the file as unsigned XML files,
                # recursively call this function with new data
                if xml_content := remove_signature(file_data['content']):
                    if to_process_new := attachment._decode_edi_xml(f"{parts[:1]}.xml", xml_content):
                        to_process += to_process_new
                        continue
            to_process.append(file_data)
        return to_process
