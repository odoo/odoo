# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import logging
import requests
import werkzeug.utils

from PIL import Image
from odoo import http, tools
from odoo.http import request

logger = logging.getLogger(__name__)


class Web_Unsplash(http.Controller):

    # ------------------------------------------------------
    # add unsplash image url
    # ------------------------------------------------------
    @http.route('/web_unsplash/attachment/add', type='json', auth='user', methods=['POST'])
    def save_unsplash_url(self, unsplashurls=None, **kwargs):
        """
            unsplashurls = {
                image_id1: image_url1,
                image_id2: image_url2,
                .....
            }
        """
        if not unsplashurls:
            return []

        uploads = []
        Attachments = request.env['ir.attachment']

        res_model = kwargs.get('res_model', 'ir.ui.view')
        if res_model != 'ir.ui.view' and kwargs.get('res_id'):
            res_id = int(kwargs['res_id'])
        else:
            res_id = None

        for key in unsplashurls:
            url = unsplashurls[key].get('url')
            try:
                req = requests.get(url)
                if req.status_code != requests.codes.ok:
                    continue

                # get mime-type of image url because unsplash url dosn't contains mime-types in url
                mimetype = req.headers.get('Content-Type')
                datas = req.content
            except requests.exceptions.ConnectionError as e:
                logger.exception("Connection Error: " + str(e))
                continue
            except requests.exceptions.Timeout as e:
                logger.exception("Timeout: " + str(e))
                continue

            image = Image.open(io.BytesIO(datas))
            image_format = image.format

            # optimized image before save
            if image_format and image_format in ('PNG', 'JPEG'):
                datas = tools.image_save_for_web(image)

            name = key
            # append image extension in name
            if image_format:
                name += '.' + image_format.lower()

            attachment = Attachments.create({
                'name': name,
                'datas_fname': name,
                'mimetype': mimetype,
                'datas': base64.b64encode(datas),
                'public': res_model == 'ir.ui.view',
                'res_id': res_id,
                'res_model': res_model,
            })
            attachment.generate_access_token()
            uploads.extend(attachment.read(['name', 'mimetype', 'checksum', 'res_id', 'res_model', 'access_token']))

        return uploads

    @http.route("/web_unsplash/get_client_id", type='json', auth="user")
    def get_unsplash_client_id(self, **post):
        if request.env.user._has_unsplash_key_rights():
            return request.env['ir.config_parameter'].sudo().get_param('unsplash.access_key')
        raise werkzeug.exceptions.NotFound()

    @http.route("/web_unsplash/set_client_id", type='json', auth="user")
    def set_unsplash_client_id(self, key, **post):
        if request.env.user._has_unsplash_key_rights():
            return request.env['ir.config_parameter'].sudo().set_param('unsplash.access_key', key)
        raise werkzeug.exceptions.NotFound()
