from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_import_file_type(self, file_data):
        """ Identify PINT JP files. """
        # EXTENDS 'account_edi_ubl_cii'
        tree = file_data['xml_tree']
        if tree is not None and tree.findtext('{*}CustomizationID') == 'urn:peppol:pint:billing-1@jp-1':
            return 'account.edi.xml.pint_jp'

        return super()._get_import_file_type(file_data)
