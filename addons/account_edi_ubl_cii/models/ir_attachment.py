# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _identify_and_unwrap_file(self, file_data):
        """ Identify UBL files. """
        # EXTENDS 'account'
        if (
            'xml_tree' in file_data and
            self.env['account.move']._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree']) is not None
        ):
            return [{**file_data, 'type': 'account_edi_ubl_cii', 'priority': 20}]

        return super()._identify_and_unwrap_file(file_data)
