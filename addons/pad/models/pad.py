# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import re
import string

import requests

from odoo import api, models, _
from odoo.exceptions import UserError

from ..py_etherpad import EtherpadLiteClient

_logger = logging.getLogger(__name__)


class PadCommon(models.AbstractModel):
    _name = 'pad.common'

    @api.model
    def pad_is_configured(self):
        return bool(self.env.user.company_id.pad_server)

    @api.model
    def pad_generate_url(self):
        company = self.env.user.sudo().company_id

        pad = {
            "server": company.pad_server,
            "key": company.pad_key,
        }

        # make sure pad server in the form of http://hostname
        if not pad["server"]:
            return pad
        if not pad["server"].startswith('http'):
            pad["server"] = 'http://' + pad["server"]
        pad["server"] = pad["server"].rstrip('/')
        # generate a salt
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.SystemRandom().randint(0, len(s) - 1)] for i in range(10)])
        # path
        # etherpad hardcodes pad id length limit to 50
        path = '-%s-%s' % (self._name, salt)
        path = '%s%s' % (self.env.cr.dbname.replace('_', '-')[0:50 - len(path)], path)
        # contruct the url
        url = '%s/p/%s' % (pad["server"], path)

        # if create with content
        if self.env.context.get('field_name') and self.env.context.get('model') and self.env.context.get('object_id'):
            myPad = EtherpadLiteClient(pad["key"], pad["server"] + '/api')
            try:
                myPad.createPad(path)
            except IOError:
                raise UserError(_("Pad creation failed, either there is a problem with your pad server URL or with your connection."))

            # get attr on the field model
            model = self.env[self.env.context["model"]]
            field = model._fields[self.env.context['field_name']]
            real_field = field.pad_content_field

            # get content of the real field
            for record in model.browse([self.env.context["object_id"]]):
                if record[real_field]:
                    myPad.setHtmlFallbackText(path, record[real_field])

        return {
            "server": pad["server"],
            "path": path,
            "url": url,
        }

    @api.model
    def pad_get_content(self, url):
        company = self.env.user.sudo().company_id
        myPad = EtherpadLiteClient(company.pad_key, (company.pad_server or '') + '/api')
        content = ''
        if url:
            split_url = url.split('/p/')
            path = len(split_url) == 2 and split_url[1]
            try:
                content = myPad.getHtml(path).get('html', '')
            except IOError:
                _logger.warning('Http Error: the credentials might be absent for url: "%s". Falling back.' % url)
                try:
                    r = requests.get('%s/export/html' % url)
                    r.raise_for_status()
                except Exception:
                    _logger.warning("No pad found with url '%s'.", url)
                else:
                    mo = re.search('<body>(.*)</body>', r.content.decode(), re.DOTALL)
                    if mo:
                        content = mo.group(1)

        return content

    # TODO
    # reverse engineer protocol to be setHtml without using the api key

    @api.multi
    def write(self, vals):
        self._set_field_to_pad(vals)
        self._set_pad_to_field(vals)
        return super(PadCommon, self).write(vals)

    @api.model
    def create(self, vals):
        # Case of a regular creation: we receive the pad url, so we need to update the
        # corresponding field
        self._set_pad_to_field(vals)
        pad = super(PadCommon, self).create(vals)

        # Case of a programmatical creation (e.g. copy): we receive the field content, so we need
        # to create the corresponding pad
        if self.env.context.get('pad_no_create', False):
            return pad
        for k, field in self._fields.items():
            if hasattr(field, 'pad_content_field') and k not in vals:
                ctx = {
                    'model': self._name,
                    'field_name': k,
                    'object_id': pad.id,
                }
                pad_info = self.with_context(**ctx).pad_generate_url()
                pad[k] = pad_info.get('url')
        return pad

    def _set_field_to_pad(self, vals):
        # Update the pad if the `pad_content_field` is modified
        for k, field in self._fields.items():
            if hasattr(field, 'pad_content_field') and vals.get(field.pad_content_field) and self[k]:
                company = self.env.user.sudo().company_id
                myPad = EtherpadLiteClient(company.pad_key, (company.pad_server or '') + '/api')
                path = self[k].split('/p/')[1]
                myPad.setHtmlFallbackText(path, vals[field.pad_content_field])

    def _set_pad_to_field(self, vals):
        # Update the `pad_content_field` if the pad is modified
        for k, v in list(vals.items()):
            field = self._fields.get(k)
            if hasattr(field, 'pad_content_field'):
                vals[field.pad_content_field] = self.pad_get_content(v)
