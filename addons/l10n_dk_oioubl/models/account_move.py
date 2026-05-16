from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_import_file_type(self, file_data):
        """ Identify OIOUBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None
            and (customization_id := file_data['xml_tree'].findtext('{*}CustomizationID'))
            and customization_id == 'OIOUBL-2.01'
        ):
            return 'account.edi.xml.oioubl_201'

        return super()._get_import_file_type(file_data)
