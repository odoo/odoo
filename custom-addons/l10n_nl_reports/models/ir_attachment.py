# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from lxml import etree

from odoo import api, models, tools

_logger = logging.getLogger(__name__)

XSD_INFO = {
    'name': 'XmlAuditfileFinancieel3.2.xsd',
    'url': 'https://www.softwarepakketten.nl/upload/auditfiles/xaf/20140402_AuditfileFinancieelVersie_3_2.zip',
    'prefix': 'l10n_nl_reports',
}

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py
        tools.load_xsd_files_from_url(self.env, XSD_INFO['url'], xsd_name_prefix=XSD_INFO['prefix'])
        super().action_download_xsd_files()

    @api.model
    def l10n_nl_reports_validate_xml_from_attachment(self, xml_content):
        return tools.validate_xml_from_attachment(self.env, xml_content, XSD_INFO['name'], prefix=XSD_INFO['prefix'])

    @api.model
    def l10n_nl_reports_load_iso_country_codes(self):
        xsd_name = f"{XSD_INFO['prefix']}.{XSD_INFO['name']}"
        attachment = self.search([('name', '=', xsd_name)], limit=1)

        if not attachment:
            return set()

        country_code_container = etree.fromstring(attachment.raw).find(
            './/{http://www.w3.org/2001/XMLSchema}simpleType[@name="CountrycodeIso3166"]')
        return set(
            e.attrib['value']
            for e in country_code_container.findall('.//{http://www.w3.org/2001/XMLSchema}enumeration')
        )
