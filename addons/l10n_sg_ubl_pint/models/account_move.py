import uuid

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_sg_get_uuid(self):
        """ SG Pint requires us to generate a uuid, to avoid storing a new field on the move,
        we derive it from the dbuuid and the move id. """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        guid = uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(self.id))
        return str(guid)

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and customization_id.text == 'urn:peppol:pint:billing-1@sg-1':
            return self.env['account.edi.xml.pint_sg']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)
