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

    def _l10n_es_tbai_create_xsd_attachment(self, name, xsd, description=None):
        attachment = self.env['ir.attachment'].create({
            'name': name,
            'description': description,
            'datas': base64.encodebytes(xsd),
            'company_id': False,
        })
        self.env['ir.model.data'].create({
            'name': name,
            'module': 'l10n_es_tbai',
            'res_id': attachment.id,
            'model': 'ir.attachment',
            'noupdate': True,
        })
        _logger.info("Created XSD attachment: " + name)

    def _l10n_es_tbai_load_xsd_core(self):
        file_name = "xmldsig-core-schema.xsd"
        attachment = self.env.ref(file_name, False)
        if attachment:
            return

        response = self._l10n_es_tbai_get_url_content("https://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd")
        if response is None:
            return

        try:
            xsd_object = objectify.fromstring(bytes(response.text, "utf-8"))
        except etree.XMLSyntaxError as e:
            _logger.warning('You are trying to load an invalid xsd file.\n%s', e)
            return
        validated_content = etree.tostring(xsd_object, pretty_print=True)
        self._l10n_es_tbai_create_xsd_attachment(file_name, validated_content, "Core schema, locally imported by schemas")

    def _l10n_es_tbai_load_xsd_schemas(self):
        # This method only downloads the xsd files if they don't exist as attachments

        response = self._l10n_es_tbai_get_url_content(self.env.company.l10n_es_tbai_url_xsd)
        if response is None:
            return

        try:
            archive = zipfile.ZipFile(io.BytesIO(response.content))
        except Exception:
            _logger.warning('UNZIP for XSD failed from URL: %s', self.env.company.l10n_es_tbai_url_xsd)
            return

        for file_name in archive.namelist():
            if not file_name or not file_name.endswith("ticketBaiV1-2.xsd"):
                continue

            attachment_name = f'{self.env.company.l10n_es_tbai_tax_agency}_{file_name}'
            attachment = self.env.ref(attachment_name, False)
            if attachment:
                continue

            content = archive.read(file_name)
            try:
                # xmldsig is found by custom parser in odoo.tools._check_with_xsd
                # module name not used by odoo resolver for schemaLocation
                content = content.replace(b'schemaLocation="http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd"', b'schemaLocation="xmldsig-core-schema.xsd"')
                xsd_object = objectify.fromstring(content)
            except etree.XMLSyntaxError as e:
                _logger.warning('You are trying to load an invalid xsd file.\n%s', e)
                return
            validated_content = etree.tostring(xsd_object, pretty_print=True)
            self._l10n_es_tbai_create_xsd_attachment(
                attachment_name, validated_content,
                "XSD validation schema for " + ("canceling" if "Anula" in file_name else "posting")
            )

    def _l10n_es_tbai_load_xsd_attachments(self):
        self._l10n_es_tbai_load_xsd_core()
        self._l10n_es_tbai_load_xsd_schemas()
