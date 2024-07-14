# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools


XSD_INFO = {
    'name': 'xsd_at_saft.xsd',
    'url': 'https://www.bmf.gv.at/dam/jcr:3c407d8c-5657-47a7-90fc-e152d884fe42/SAF-T_AT_1.01.xsd',
    'prefix': 'l10n_at_saft',
}


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_at_saft_load_xsd_files(self, force_reload=False):
        tools.load_xsd_files_from_url(self.env, XSD_INFO['url'], XSD_INFO['name'], xsd_name_prefix=XSD_INFO['prefix'])

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py
        self._l10n_at_saft_load_xsd_files()
        super().action_download_xsd_files()

    @api.model
    def l10n_at_saft_validate_xml_from_attachment(self, xml_content, xsd_name=None):
        return tools.validate_xml_from_attachment(self.env, xml_content, XSD_INFO['name'], prefix=XSD_INFO['prefix'])
