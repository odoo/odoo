# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_import_type_and_priority(self, file_data):
        """ Identify UBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None and
            self.env['account.move']._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree']) is not None
        ):
            return ('account_edi_ubl_cii', 20)

        return super()._get_import_type_and_priority(file_data)
