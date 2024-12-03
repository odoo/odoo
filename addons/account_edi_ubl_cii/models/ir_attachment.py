# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_import_type_and_priority(self):
        """ Identify UBL files. """
        # EXTENDS 'account'
        if (
            self.xml_tree is not False and
            self.env['account.move']._get_ubl_cii_builder_from_xml_tree(self.xml_tree) is not None
        ):
            return ('account_edi_ubl_cii', 20)

        return super()._get_import_type_and_priority()
