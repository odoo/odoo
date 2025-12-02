from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_import_file_type(self, file_data):
        """ Identify OIOUBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None
            and (customization_id := file_data['xml_tree'].findtext('{*}CustomizationID'))
            and 'OIOUBL-2' in customization_id
        ):
            return 'account.edi.xml.oioubl_201'

        return super()._get_import_file_type(file_data)
