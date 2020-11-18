# -*- coding: utf-8 -*-

import base64
import io
import logging
import requests
import zipfile
from os.path import join
from lxml import etree, objectify

from odoo import models, tools, _

_logger = logging.getLogger(__name__)


class Attachment(models.Model):
    _inherit = "ir.attachment"

    def _get_urls(self):
        """
        :return dict: return dict with module name and list of url information to load XSDs

        example return value,
        return {
            'module_name': {
                'urls_info': [{
                    'url': '',
                    'file_name': '', # name of desired XSD file to be extracted from ZIP/RAR file from 'url'
                    'to_modify': False, # True if downloaded XSDs needs post-processing (see l10n_lu_saft for example)
                }]
            }
        """
        return {
        }

    def _modify_xsd_content(self, content, module_name):
        """
        :return string: returns stringified content
        :param content: file content as bytes
        :param module_name: name of the module which is invoking this function(to be used by overridden methods)
        """
        return content

    def _extract_xsd_from_archive(self, content, file_name, url, module_name):
        # If an XSD file is to be extracted from other than ZIP files then this
        # method can be overridden and it must return XSD content at the end.
        """
        :return bytes: return read bytes
        :param content: file content as bytes
        :param file_name: the file name to be extracted from compressed file
        :param url: url of archive file
        :param module_name: name of the module which is invoking this function
        """
        bytes_content = io.BytesIO(content)
        if not zipfile.is_zipfile(bytes_content):
            _logger.warning(_("No archive file found at URL %s. Verify the URL and "
                              "correct it in %s module's _get_urls(...) method.") % (url, module_name))
            return b''
        file = ''
        with zipfile.ZipFile(bytes_content) as archive:
            for file_path in archive.namelist():
                if file_name in file_path:
                    file = file_path
                    break
            try:
                return archive.open(file).read()
            except KeyError as e:
                _logger.warning(_("File '%s' not found at URL %s. Check module %s _get_urls(...) method.")
                                % (file_name, url, module_name))
                return b''

    def _stringify_xsd_object(self, xsd_object):
        """
        :return string: returns stringified content
        :param xsd_object: objectified file content
        """
        try:
            xsd_string = etree.tostring(xsd_object, pretty_print=True)
        except etree.XMLSyntaxError:
            _logger.warning('XSD file downloaded is not valid.')
            return ''
        if not xsd_string:
            _logger.warning('XSD file downloaded is empty.')
            return ''
        return xsd_string

    def _validate_xsd_content(self, content, module_name):
        """
        :return object: returns ObjectifiedElement
        :param content: file content as bytes
        """
        try:
            return objectify.fromstring(content)
        except etree.XMLSyntaxError:
            _logger.warning(_('You are trying to load an invalid xsd file for module %s.') % (module_name,))
            return ''

    def _load_xsd_files(self, reload_app_list=None, modified_urls_info=None):
        """
        :return list: returns list of filestore path or files downloaded from URL
        :param reload_app_list: list
        :param modified_urls_info: dict
        """
        if reload_app_list:
            # This provides flexibility to users if they want to delete and reload the XSDs. For that,
            # user can just pass the module name as a list to the parameter of the method used in cron.
            imd_records = self.env['ir.model.data'].search([
                ('name', 'like', 'xsd_cached_%'),
                ('module', 'in', reload_app_list)
            ])
            xsd_files = ['%s.%s' % (x.module, x.name) for x in imd_records]
            for xsd in xsd_files:
                self.env.ref(xsd).unlink()

        attachments = self.env['ir.attachment']
        urls_info = modified_urls_info or self._get_urls()
        for module_name, values in urls_info.items():
            for url_info in values.get('urls_info', []):
                url = url_info['url']
                file_name = url_info.get('file_name') or ''
                to_modify = url_info.get('to_modify')
                # step 1: Extract filename from URL and check if it was already stored in attachment.
                fname = file_name or url.split('/')[-1]
                xsd_fname = 'xsd_cached_%s' % fname.replace('.', '_')
                attachment = self.env.ref('%s.%s' % (module_name, xsd_fname), False)
                if attachment:
                    continue
                # step 2: Check if the URL is valid.
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.warning(_('I cannot connect with the given URL %s.') % (url))
                    continue
                '''
                step 3: Identify if the URL has plain XSD file or if it has a ZIP file, if it's
                        a ZIP file then extract the desired XSD file and return its content.
                '''
                content = response.content
                if file_name:
                    content = self._extract_xsd_from_archive(content, file_name, url, module_name)
                # step 4: Post process XSD to add some content in it.
                if to_modify:
                    # Some XSD files requires modification after downloaded from original source.
                    # See l10n_lu_saft/l10n_mx_edi to find out situations when XSD needs modification.
                    content = self._modify_xsd_content(content, module_name)
                # step 5: Validate the content one final time as it could have modified.
                xsd_object = self._validate_xsd_content(content, module_name)
                if not len(xsd_object):
                    continue
                # step 6: Create the attachment and ir.model.data entry.
                attachment = self.create({
                    'name': xsd_fname,
                    'datas': base64.encodebytes(content),
                })
                self.env['ir.model.data'].create({
                    'name': xsd_fname,
                    'module': module_name,
                    'res_id': attachment.id,
                    'model': 'ir.attachment',
                    'noupdate': True
                })
                attachments += attachment
        filestore = tools.config.filestore(self.env.cr.dbname)
        return [join(filestore, attachment.store_fname) for attachment in attachments]
