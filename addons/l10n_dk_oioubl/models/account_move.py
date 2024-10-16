from odoo import api, models
from odoo.addons import account_edi_ubl_cii


class AccountMove(account_edi_ubl_cii.AccountMove):

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'OIOUBL-2' in customization_id.text:
            return self.env['account.edi.xml.oioubl_201']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)
