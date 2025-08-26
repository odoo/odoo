# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json
import logging
import re
import time
import requests
from lxml import etree
from base64 import b64decode
from math import floor
from os.path import join as opj

from odoo.http import request, Response
from odoo import http, tools, _
from odoo.tools.misc import file_open


logger = logging.getLogger(__name__)
DEFAULT_LIBRARY_ENDPOINT = 'https://media-api.odoo.com'
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'


def get_existing_attachment(IrAttachment, vals):
    """
    Check if an attachment already exists for the same vals. Return it if
    so, None otherwise.
    """
    fields = dict(vals)
    # Falsy res_id defaults to 0 on attachment creation.
    fields['res_id'] = fields.get('res_id') or 0
    raw, datas = fields.pop('raw', None), fields.pop('datas', None)
    domain = [(field, '=', value) for field, value in fields.items()]
    if fields.get('type') == 'url':
        if 'url' not in fields:
            return None
        domain.append(('checksum', '=', False))
    else:
        if not (raw or datas):
            return None
        domain.append(('checksum', '=', IrAttachment._compute_checksum(raw or b64decode(datas))))
    return IrAttachment.search(domain, limit=1) or None

class Web_Editor(http.Controller):

    #------------------------------------------------------
    # Update a checklist in the editor on check/uncheck
    #------------------------------------------------------
    @http.route('/web_editor/checklist', type='jsonrpc', auth='user')
    def update_checklist(self, res_model, res_id, filename, checklistId, checked, **kwargs):
        record = request.env[res_model].browse(res_id)
        value = filename in record._fields and record.read([filename])[0][filename]
        htmlelem = etree.fromstring("<div>%s</div>" % value, etree.HTMLParser())
        checked = bool(checked)

        li = htmlelem.find(".//li[@id='checkId-%s']" % checklistId)

        if li is None:
            return value

        classname = li.get('class', '')
        if ('o_checked' in classname) != checked:
            if checked:
                classname = '%s o_checked' % classname
            else:
                classname = re.sub(r"\s?o_checked\s?", '', classname)
            li.set('class', classname)
        else:
            return value

        value = etree.tostring(htmlelem[0][0], encoding='utf-8', method='html')[5:-6].decode("utf-8")
        record.write({filename: value})

        return value

    #------------------------------------------------------
    # Update a stars rating in the editor on check/uncheck
    #------------------------------------------------------
    @http.route('/web_editor/stars', type='jsonrpc', auth='user')
    def update_stars(self, res_model, res_id, filename, starsId, rating):
        record = request.env[res_model].browse(res_id)
        value = filename in record._fields and record.read([filename])[0][filename]
        htmlelem = etree.fromstring("<div>%s</div>" % value, etree.HTMLParser())

        stars_widget = htmlelem.find(".//span[@id='checkId-%s']" % starsId)

        if stars_widget is None:
            return value

        # Check the `rating` first stars and uncheck the others if any.
        stars = []
        for star in stars_widget.getchildren():
            if 'fa-star' in star.get('class', ''):
                stars.append(star)
        star_index = 0
        for star in stars:
            classname = star.get('class', '')
            if star_index < rating and (not 'fa-star' in classname or 'fa-star-o' in classname):
                classname = re.sub(r"\s?fa-star-o\s?", '', classname)
                classname = '%s fa-star' % classname
                star.set('class', classname)
            elif star_index >= rating and not 'fa-star-o' in classname:
                classname = re.sub(r"\s?fa-star\s?", '', classname)
                classname = '%s fa-star-o' % classname
                star.set('class', classname)
            star_index += 1

        value = etree.tostring(htmlelem[0][0], encoding='utf-8', method='html')[5:-6]
        record.write({filename: value})

        return value

    @http.route('/web_editor/tests', type='http', auth="user")
    def test_suite(self, mod=None, **kwargs):
        return request.render('web_editor.tests')

