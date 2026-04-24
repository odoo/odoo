# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import mimetypes
import requests
import werkzeug.utils
from werkzeug.urls import url_encode

from odoo import http, modules, _
from odoo.tools.image import image_process
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.html_editor.controllers.main import attachment_create

logger = logging.getLogger(__name__)

UNSPLASH_APP_ID_ICP = 'unsplash.app_id'
UNSPLASH_ACCESS_KEY_ICP = 'unsplash.access_key'


class Web_Unsplash(http.Controller):

    def _get_access_key(self):
        """ Use this method to get the key, needed for internal reason """
        return self.env['ir.config_parameter'].sudo().get_str(UNSPLASH_ACCESS_KEY_ICP)

    def _notify_download(self, url):
        ''' Notifies Unsplash from an image download. (API requirement)
            :param url: the download_url of the image to be notified

            This method won't return anything. This endpoint should just be
            pinged with a simple GET request for Unsplash to increment the image
            view counter.
        '''
        try:
            if not url.startswith('https://api.unsplash.com/photos/') and not modules.module.current_test:
                raise Exception(_("ERROR: Unknown Unsplash notify URL!"))
            access_key = self._get_access_key()
            requests.get(url, params=url_encode({'client_id': access_key}))
        except Exception as e:
            logger.exception("Unsplash download notification failed: " + str(e))

    # ------------------------------------------------------
    # add unsplash image url
    # ------------------------------------------------------
    @http.route('/web_unsplash/attachment/add', type='jsonrpc', auth='user', methods=['POST'])
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
                if not url.startswith(('https://images.unsplash.com/', 'https://plus.unsplash.com/')) and not modules.module.current_test:
                    logger.exception("ERROR: Unknown Unsplash URL!: " + url)
                    raise Exception(_("ERROR: Unknown Unsplash URL!"))

                req = requests.get(url)
                if req.status_code != requests.codes.ok:
                    continue

                # get mime-type of image url because unsplash url dosn't contains mime-types in url
                image = req.content
            except requests.exceptions.ConnectionError as e:
                logger.exception("Connection Error: " + str(e))
                continue
            except requests.exceptions.Timeout as e:
                logger.exception("Timeout: " + str(e))
                continue

            image = image_process(image, verify_resolution=True)
            mimetype = guess_mimetype(image)
            # append image extension in name
            query += mimetypes.guess_extension(mimetype) or ''

            # /unsplash/5gR788gfd/lion
            url_frags = ['unsplash', key, query]

            attachment_data = {
                'name': '_'.join(url_frags),
                'data': image,
                'res_id': res_id,
                'res_model': res_model,
            }
            attachment = attachment_create(self.env['ir.attachment'], **attachment_data)
            # Creating an attachment with binary type and URL is normally forbidden
            # See `_check_serving_attachments`
            # However, we want to bypass this protection for unsplash images
            attachment.sudo().url = '/' + '/'.join(url_frags)
            if value.get('description'):
                attachment.description = value.get('description')
            attachment.generate_access_token()
            uploads.append(attachment._get_media_info())

            # Notifies Unsplash from an image download. (API requirement)
            self._notify_download(value.get('download_url'))

        return uploads

    @http.route("/web_unsplash/fetch_images", type='jsonrpc', auth="user")
    def fetch_unsplash_images(self, **post):
        return self.env['ir.attachment']._fetch_unsplash_images(**post)

    @http.route("/web_unsplash/get_app_id", type='jsonrpc', auth="public")
    def get_unsplash_app_id(self, **post):
        return self.env['ir.config_parameter'].sudo().get_str(UNSPLASH_APP_ID_ICP)

    @http.route("/web_unsplash/save_unsplash", type='jsonrpc', auth="user")
    def save_unsplash(self, **post):
        if self.env.user._can_manage_unsplash_settings():
            self.env['ir.config_parameter'].sudo().set_str(UNSPLASH_APP_ID_ICP, post.get('appId'))
            self.env['ir.config_parameter'].sudo().set_str(UNSPLASH_ACCESS_KEY_ICP, post.get('key'))
            return True
        raise werkzeug.exceptions.NotFound()
