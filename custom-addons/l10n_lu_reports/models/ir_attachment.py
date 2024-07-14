# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools


XSD_INFO = {
    'ecdf': {
        'name': 'xsd_lu_eCDF.xsd',
        'url': 'https://ecdf-developer.b2g.etat.lu/ecdf/formdocs/eCDF_file_v2.0-XML_schema.xsd',
        'prefix': 'l10n_lu_reports',
    },
    'saft': {
        'name': 'FAIA_v_2.01_reduced_version_A.xsd',
        'url': 'https://pfi.public.lu/dam-assets/backup/FAIA/FAIA/XSD_Files.zip',
        'prefix': 'l10n_lu_reports',
    }
}


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_lu_reports_load_xsd_files(self, force_reload=False):
        def modify_xsd_content(content):
            return content.replace(b'<xsd:pattern value="[\\P{Cc}]+" />', b'')

        for xsd_info in XSD_INFO.values():
            tools.load_xsd_files_from_url(self.env, xsd_info['url'], xsd_info['name'], xsd_name_prefix=xsd_info['prefix'], modify_xsd_content=modify_xsd_content)

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py
        self._l10n_lu_reports_load_xsd_files()
        super().action_download_xsd_files()

    @api.model
    def l10n_lu_reports_validate_xml_from_attachment(self, xml_content, document_type):
        return tools.validate_xml_from_attachment(self.env, xml_content, XSD_INFO[document_type]['name'], prefix=XSD_INFO[document_type]['prefix'])
