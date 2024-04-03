# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_agencies import get_key
from odoo.tools import xml_utils


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def action_download_xsd_files(self):
        """
        Downloads the TicketBAI XSD validation files if they don't already exist, for the active tax agency.
        """
        xml_utils.load_xsd_files_from_url(
            self.env, 'https://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd', 'xmldsig-core-schema.xsd',
            xsd_name_prefix='l10n_es_edi_tbai')

        for agency in ['gipuzkoa', 'araba', 'bizkaia']:
            urls = get_key(agency, 'xsd_url')
            names = get_key(agency, 'xsd_name')
            # For Bizkaia, one url per XSD (post/cancel)
            if isinstance(urls, dict):
                for move_type in ('post', 'cancel'):
                    xml_utils.load_xsd_files_from_url(
                        self.env, urls[move_type], names[move_type],
                        xsd_name_prefix='l10n_es_edi_tbai',
                    )
            # For other agencies, single url to zip file (only keep the desired names)
            else:
                xml_utils.load_xsd_files_from_url(
                    self.env, urls,  # NOTE: file_name discarded when XSDs bundled in ZIPs
                    xsd_name_prefix='l10n_es_edi_tbai',
                    xsd_names_filter=list(names.values()),
                )
        return super().action_download_xsd_files()
