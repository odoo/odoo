import uuid

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_sg_get_uuid(self):
        """ SG Pint requires us to generate a uuid, to avoid storing a new field on the move,
        we derive it from the dbuuid and the move id. """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        guid = uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(self.id))
        return str(guid)

    def _get_import_file_type(self, file_data):
        """ Identify PINT SG files. """
        # EXTENDS 'account_edi_ubl_cii'
        tree = file_data['xml_tree']
        if tree is not None and tree.findtext('{*}CustomizationID') == 'urn:peppol:pint:billing-1@sg-1':
            return 'account.edi.xml.pint_sg'

        return super()._get_import_file_type(file_data)
