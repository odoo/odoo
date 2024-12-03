# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    def _identify_and_unwrap_file(self, file_data):
        """ If the file matches one of the UBL formats, set the decoder. """
        # EXTENDS 'account'
        if (
            'xml_tree' in file_data and
            (ubl_cii_xml_builder := self.env['account.move']._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])) is not None
        ):
            return [{**file_data, 'type': ubl_cii_xml_builder._name, 'decoder': ubl_cii_xml_builder._import_invoice_ubl_cii, 'priority': 20}]

        return super()._identify_and_unwrap_file(file_data)
