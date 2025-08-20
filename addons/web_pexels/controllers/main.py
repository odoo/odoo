# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import mimetypes
import requests
import werkzeug.utils
from werkzeug.urls import url_encode

from odoo import http, tools, _
from odoo.http import request
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.html_editor.controllers.main import HTML_Editor

_logger = logging.getLogger(__name__)


class Web_Pexels(http.Controller):

    def _get_api_key(self):
        """ Use this method to get the key, needed for internal reason """
        return request.env['ir.config_parameter'].sudo().get_param('pexels.api_key')

    @http.route('/web_pexels/attachment/add', type='json', auth='user', methods=['POST'])
    def save_pexels_url(self, pexelsurls=None, **kwargs):
        """
            pexelshurls = {
                image_id1: {
                    url: image_url,
                    download_url: download_url,
                },
                image_id2: {
                    url: image_url,
                    download_url: download_url,
                },
                .....
            }
        """
        def slugify(s):
            ''' Keeps only alphanumeric characters, hyphens and spaces from a string.
                The string will also be truncated to 1024 characters max.
                :param s: the string to be filtered
                :return: the sanitized string
            '''
            return "".join([c for c in s if c.isalnum() or c in list("- ")])[:1024]

        if not pexelsurls:
            return []

        uploads = []

        query = kwargs.get('query', '')
        query = slugify(query)

        res_model = kwargs.get('res_model', 'ir.ui.view')
        if res_model != 'ir.ui.view' and kwargs.get('res_id'):
            res_id = int(kwargs['res_id'])
        else:
            res_id = None

        for key, value in pexelsurls.items():
            url = value.get('url')
            try:
                if not url.startswith('https://images.pexels.com/') and not request.env.registry.in_test_mode():
                    _logger.exception("ERROR: Unknown Pexels URL!: %s", url)
                    raise Exception(_("ERROR: Unknown Pexels URL!"))

                req = requests.get(url)
                if req.status_code != requests.codes.ok:
                    continue

                # JKE TODO
                # get mime-type of image url because pexels url doesn't contains mime-types in url
                image = req.content
            except requests.exceptions.ConnectionError as e:
                _logger.exception("Connection Error: %s", str(e))
                continue
            except requests.exceptions.Timeout as e:
                _logger.exception("Timeout: %s", str(e))
                continue

            image = tools.image_process(image, verify_resolution=True)
            mimetype = guess_mimetype(image)
            # append image extension in name
            query += mimetypes.guess_extension(mimetype) or ''

            # /pexels/5gR788gfd/lion
            url_frags = ['pexels', key, query]

            attachment_data = {
                'name': '_'.join(url_frags),
                'url': '/' + '/'.join(url_frags),
                'data': image,
                'res_id': res_id,
                'res_model': res_model,
            }
            attachment = HTML_Editor._attachment_create(self, **attachment_data)
            if value.get('description'):
                attachment.description = value.get('description')
            attachment.generate_access_token()
            uploads.append(attachment._get_media_info())

        return uploads

    @http.route("/web_pexels/fetch_images", type='json', auth="user")
    def fetch_pexels_images(self, **post):
        api_key = self._get_api_key()
        if not api_key:
            if not request.env.user._can_manage_pexels_settings():
                return {'error': 'no_access'}
            return {'error': 'key_not_found'}
        response = requests.get('https://api.pexels.com/v1/search/', params=url_encode(post), headers={"Authorization": api_key})
        if response.status_code == requests.codes.ok:
            return response.json()
        else:
            if not request.env.user._can_manage_pexels_settings():
                return {'error': 'no_access'}
            return {'error': response.status_code}

    @http.route("/web_pexels/save_pexels", type='json', auth="user")
    def save_pexels(self, **post):
        if request.env.user._can_manage_pexels_settings():
            request.env['ir.config_parameter'].sudo().set_param('pexels.api_key', post.get('key'))
            return True
        raise werkzeug.exceptions.NotFound()
