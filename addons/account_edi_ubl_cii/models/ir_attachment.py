# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_import_file_type(self, file_data):
        """ Identify UBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None and
            self.env['account.move']._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree']) is not None
        ):
            return 'account_edi_ubl_cii'

        return super()._get_import_file_type(file_data)
