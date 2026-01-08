from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'OIOUBL-2' in customization_id.text:
            return self.env['account.edi.xml.oioubl_201']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)
