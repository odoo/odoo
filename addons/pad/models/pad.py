# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import re
import string

import requests

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

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
                    myPad.setText(path, (html2plaintext(record[real_field]).encode('utf-8')))
                    # Etherpad for html not functional
                    # myPad.setHTML(path, record[real_field])

        return {
            "server": pad["server"],
            "path": path,
            "url": url,
        }

    @api.model
    def pad_get_content(self, url):
        content = ''
        if url:
            try:
                r = requests.get('%s/export/html' % url)
                r.raise_for_status()
            except:
                _logger.warning("No url found '%s'.", url)
            else:
                mo = re.search('<body>(.*)</body>', r.content.decode(), re.DOTALL)
                if mo:
                    content = mo.group(1)

        return content

    # TODO
    # reverse engineer protocol to be setHtml without using the api key

    @api.multi
    def write(self, vals):
        self._set_pad_value(vals)
        return super(PadCommon, self).write(vals)

    @api.model
    def create(self, vals):
        self._set_pad_value(vals)
        pad = super(PadCommon, self).create(vals)

        # In case the pad is created programmatically, the content is not filled in yet since it is
        # normally initialized by the JS layer
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

    # Set the pad content in vals
    def _set_pad_value(self, vals):

        # Update the pad if the `pad_content_field` is modified
        for k, field in self._fields.items():
            if hasattr(field, 'pad_content_field') and vals.get(field.pad_content_field) and self[k]:
                company = self.env.user.sudo().company_id
                myPad = EtherpadLiteClient(company.pad_key, company.pad_server + '/api')
                path = self[k].split('/p/')[1]
                myPad.setText(path, (html2plaintext(vals[field.pad_content_field]).encode('utf-8')))

        # Update the `pad_content_field` if the pad is modified
        for k, v in list(vals.items()):
            field = self._fields[k]
            if hasattr(field, 'pad_content_field'):
                vals[field.pad_content_field] = self.pad_get_content(v)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        if not default:
            default = {}
        for k, field in self._fields.items():
            if hasattr(field, 'pad_content_field'):
                if self.env.context.get('pad_no_create', False):
                    default[k] = ''
                else:
                    pad = self.pad_generate_url()
                    default[k] = pad.get('url')
        return super(PadCommon, self).copy(default)
