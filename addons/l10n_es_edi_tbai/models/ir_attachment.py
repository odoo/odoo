# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import zipfile

import requests
from lxml import etree, objectify
from odoo import models
from requests.exceptions import RequestException

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _l10n_es_tbai_get_url_content(self, url):
        _logger.info('Downloading XSD validation files from: %s', url)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except RequestException as error:
            _logger.warning(f'Connection error {error} with the given URL: {url}')
            return None
        return response

    def _l10n_es_tbai_replace_xsd_import(self, xsd_bytes):
        # xmldsig is found by a custom parser in odoo.tools._check_with_xsd
        # note: module name not used by odoo resolver for schemaLocation
        # note: default encoding for b'' objects is utf-8
        # note: failure of .replace method does not throw errors
        return xsd_bytes.replace(b'schemaLocation="http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd"', b'schemaLocation="xmldsig-core-schema.xsd"')

    def _l10n_es_tbai_create_xsd_attachment(self, name, xsd_bytes, description=None):
        xsd_bytes = self._l10n_es_tbai_replace_xsd_import(xsd_bytes)
        xsd_bytes = xsd_bytes[xsd_bytes.find("<".encode()):]  # Remove any non-XML prefix (Bizkaia's XSDs are dirty)

        try:
            xsd_object = objectify.fromstring(xsd_bytes)
        except etree.XMLSyntaxError as e:
            _logger.warning('You are trying to load an invalid xsd file.\n%s', e)
            return
        xsd_str = etree.tostring(xsd_object, pretty_print=True)

        attachment = self.env['ir.attachment'].create({
            'name': name,
            'description': description,
            'datas': base64.encodebytes(xsd_str),
            'company_id': False,
        })
        self.env['ir.model.data'].create({
            'name': name,
            'module': 'l10n_es_edi_tbai',
            'res_id': attachment.id,
            'model': 'ir.attachment',
            'noupdate': True,
        })
        _logger.info("Created XSD attachment: " + name)

    def _l10n_es_tbai_load_xsd_file(self, file_name, url):
        attachment = self.env.ref('l10n_es_edi_tbai.' + file_name, False)
        if attachment:
            return

        response = self._l10n_es_tbai_get_url_content(url)
        if response is None:
            return

        xsd_bytes = bytes(response.text, "utf-8")
        self._l10n_es_tbai_create_xsd_attachment(file_name, xsd_bytes, "Core schema, locally imported by schemas")

    def _l10n_es_tbai_load_xsd_zip(self, url):
        response = self._l10n_es_tbai_get_url_content(url)
        if response is None:
            return

        try:
            archive = zipfile.ZipFile(io.BytesIO(response.content))
        except Exception:
            _logger.warning('UNZIP for XSD failed from URL: %s', url)
            return

        for file_name in archive.namelist():
            if not file_name or not file_name.endswith("ticketBaiV1-2.xsd"):
                continue

            attachment_name = f'{self.env.company.l10n_es_tbai_tax_agency}_{file_name}'
            attachment = self.env.ref('l10n_es_edi_tbai.' + attachment_name, False)
            if attachment:
                continue

            xsd_bytes = archive.read(file_name)
            self._l10n_es_tbai_create_xsd_attachment(
                attachment_name, xsd_bytes,
                "XSD validation schema for " + ("canceling" if "Anula" in file_name else "posting")
            )

    def _l10n_es_tbai_load_xsd_attachments(self):
        """
        This method only downloads the xsd validation schemas for the selected tax agency if they don't already exist.
        """
        url = self.env.company.get_l10n_es_tbai_url_xsd()
        if url:
            self._l10n_es_tbai_load_xsd_file("xmldsig-core-schema.xsd", "https://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd")
            # For Bizkaia, one url per file
            if isinstance(url, tuple):
                for u in url:
                    self._l10n_es_tbai_load_xsd_file(u.rsplit("/", 1)[1], u)
            # For other agencies, single url to zip file
            else:
                self._l10n_es_tbai_load_xsd_zip(url)
