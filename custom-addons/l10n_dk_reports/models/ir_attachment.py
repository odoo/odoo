# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools

XSD_INFO = {
    'name': 'Danish_SAF-T_Financial_Schema_v_1_0.xsd',
    'url': 'https://erhvervsstyrelsen.dk/sites/default/files/2023-01/Danish_SAF-T_Financial_Schema_v_1_0_0.zip',
    'prefix': 'l10n_dk',
}

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py
        tools.load_xsd_files_from_url(self.env, XSD_INFO['url'], XSD_INFO['name'], xsd_name_prefix=XSD_INFO['prefix'])
        super().action_download_xsd_files()

    @api.model
    def l10n_dk_saft_validate_xml_from_attachment(self, xml_content, xsd_name=None):
        return tools.validate_xml_from_attachment(self.env, xml_content, XSD_INFO['name'], prefix=XSD_INFO['prefix'])
