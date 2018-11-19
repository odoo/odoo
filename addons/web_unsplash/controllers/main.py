# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import logging
import requests
import werkzeug.utils

from PIL import Image
from odoo import http, tools, _
from odoo.http import request
from werkzeug.urls import url_encode

logger = logging.getLogger(__name__)


class Web_Unsplash(http.Controller):

    def _get_access_key(self):
        if request.env.user._has_unsplash_key_rights():
            return request.env['ir.config_parameter'].sudo().get_param('unsplash.access_key')
        raise werkzeug.exceptions.NotFound()

    def _notify_download(self, url):
        ''' Notifies Unsplash from an image download. (API requirement)
            :param url: the download_url of the image to be notified

            This method won't return anything. This endpoint should just be
            pinged with a simple GET request for Unsplash to increment the image
            view counter.
        '''
        try:
            if not url.startswith('https://api.unsplash.com/photos/'):
                raise Exception(_("ERROR: Unknown Unsplash notify URL!"))
            access_key = self._get_access_key()
            requests.get(url, params=url_encode({'client_id': access_key}))
        except Exception as e:
            logger.exception("Unsplash download notification failed: " + str(e))

    # ------------------------------------------------------
    # add unsplash image url
    # ------------------------------------------------------
    @http.route('/web_unsplash/attachment/add', type='json', auth='user', methods=['POST'])
    def save_unsplash_url(self, unsplashurls=None, **kwargs):
        """
            unsplashurls = {
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

        if not unsplashurls:
            return []

        uploads = []
        Attachments = request.env['ir.attachment']

        query = kwargs.get('query', '')
        query = slugify(query)

        res_model = kwargs.get('res_model', 'ir.ui.view')
        if res_model != 'ir.ui.view' and kwargs.get('res_id'):
            res_id = int(kwargs['res_id'])
        else:
            res_id = None

        for key, value in unsplashurls.items():
            url = value.get('url')
            try:
                if not url.startswith('https://images.unsplash.com/'):
                    logger.exception("ERROR: Unknown Unsplash URL!: " + url)
                    raise Exception(_("ERROR: Unknown Unsplash URL!"))
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

            # optimized image before save
            if mimetype in ('image/jpeg', 'image/png'):
                image = Image.open(io.BytesIO(datas))
                if image.format in ('PNG', 'JPEG'):
                    datas = tools.image_save_for_web(image)
                    # append image extension in name
                    query += '.' + str.lower(image.format)

            # /unsplash/5gR788gfd/lion
            url_frags = ['unsplash', key, query]

            attachment = Attachments.create({
                'name': query,
                'url': '/' + '/'.join(url_frags),
                'datas_fname': '_'.join(url_frags),
                'mimetype': mimetype,
                'datas': base64.b64encode(datas),
                'public': res_model == 'ir.ui.view',
                'res_id': res_id,
                'res_model': res_model,
            })
            attachment.generate_access_token()
            uploads.extend(attachment.read(['name', 'mimetype', 'checksum', 'res_id', 'res_model', 'access_token', 'url']))

            # Notifies Unsplash from an image download. (API requirement)
            self._notify_download(value.get('download_url'))

        return uploads

    @http.route("/web_unsplash/fetch_images", type='json', auth="user")
    def fetch_unsplash_images(self, **post):
        access_key = self._get_access_key()
        app_id = self.get_unsplash_app_id()
        if not access_key or not app_id:
            return {'error': 'key_not_found'}
        post['client_id'] = access_key
        response = requests.get('https://api.unsplash.com/search/photos/', params=url_encode(post))
        if response.status_code == requests.codes.ok:
            return response.json()
        else:
            return {'error': response.status_code}

    @http.route("/web_unsplash/get_app_id", type='json', auth="public")
    def get_unsplash_app_id(self, **post):
        return request.env['ir.config_parameter'].sudo().get_param('unsplash.app_id')

    @http.route("/web_unsplash/save_unsplash", type='json', auth="user")
    def save_unsplash(self, **post):
        if request.env.user._has_unsplash_key_rights():
            request.env['ir.config_parameter'].sudo().set_param('unsplash.app_id', post.get('appId'))
            request.env['ir.config_parameter'].sudo().set_param('unsplash.access_key', post.get('key'))
            return True
        raise werkzeug.exceptions.NotFound()
