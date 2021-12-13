# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import json
import logging
import re
import time
import werkzeug.wrappers
from PIL import Image, ImageFont, ImageDraw
from lxml import etree

from odoo.http import request
from odoo import http, tools

logger = logging.getLogger(__name__)


class Web_Editor(http.Controller):
    #------------------------------------------------------
    # convert font into picture
    #------------------------------------------------------
    @http.route([
        '/web_editor/font_to_img/<icon>',
        '/web_editor/font_to_img/<icon>/<color>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        ], type='http', auth="none")
    def export_icon_to_png(self, icon, color='#000', size=100, alpha=255, font='/web/static/lib/fontawesome/fonts/fontawesome-webfont.ttf'):
        """ This method converts an unicode character to an image (using Font
            Awesome font by default) and is used only for mass mailing because
            custom fonts are not supported in mail.
            :param icon : decimal encoding of unicode character
            :param color : RGB code of the color
            :param size : Pixels in integer
            :param alpha : transparency of the image from 0 to 255
            :param font : font path

            :returns PNG image converted from given font
        """
        # Make sure we have at least size=1
        size = max(1, min(size, 512))
        # Initialize font
        with tools.file_open(font.lstrip('/'), 'rb') as f:
            font_obj = ImageFont.truetype(f, size)

        # if received character is not a number, keep old behaviour (icon is character)
        icon = chr(int(icon)) if icon.isdigit() else icon

        # Determine the dimensions of the icon
        image = Image.new("RGBA", (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        boxw, boxh = draw.textsize(icon, font=font_obj)
        draw.text((0, 0), icon, font=font_obj)
        left, top, right, bottom = image.getbbox()

        # Create an alpha mask
        imagemask = Image.new("L", (boxw, boxh), 0)
        drawmask = ImageDraw.Draw(imagemask)
        drawmask.text((-left, -top), icon, font=font_obj, fill=alpha)

        # Create a solid color image and apply the mask
        if color.startswith('rgba'):
            color = color.replace('rgba', 'rgb')
            color = ','.join(color.split(',')[:-1])+')'
        iconimage = Image.new("RGBA", (boxw, boxh), color)
        iconimage.putalpha(imagemask)

        # Create output image
        outimage = Image.new("RGBA", (boxw, size), (0, 0, 0, 0))
        outimage.paste(iconimage, (left, top))

        # output image
        output = io.BytesIO()
        outimage.save(output, format="PNG")
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/png'
        response.data = output.getvalue()
        response.headers['Cache-Control'] = 'public, max-age=604800'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        response.headers['Connection'] = 'close'
        response.headers['Date'] = time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime())
        response.headers['Expires'] = time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(time.time()+604800*60))

        return response

    #------------------------------------------------------
    # Update a checklist in the editor on check/uncheck
    #------------------------------------------------------
    @http.route('/web_editor/checklist', type='json', auth='user')
    def update_checklist(self, res_model, res_id, filename, checklistId, checked, **kwargs):
        record = request.env[res_model].browse(res_id)
        value = getattr(record, filename, False)
        htmlelem = etree.fromstring("<div>%s</div>" % value, etree.HTMLParser())
        checked = bool(checked)

        li = htmlelem.find(".//li[@id='checklist-id-" + str(checklistId) + "']")

        if not self._update_checklist_recursive(li, checked, children=True, ancestors=True):
            return value

        value = etree.tostring(htmlelem[0][0], encoding='utf-8', method='html')[5:-6]
        record.write({filename: value})

        return value

    def _update_checklist_recursive (self, li, checked, children=False, ancestors=False):
        if 'checklist-id-' not in li.get('id', ''):
            return False

        classname = li.get('class', '')
        if ('o_checked' in classname) == checked:
            return False

        # check / uncheck
        if checked:
            classname = '%s o_checked' % classname
        else:
            classname = re.sub(r"\s?o_checked\s?", '', classname)
        li.set('class', classname)

        # propagate to children
        if children:
            node = li.getnext()
            ul = None
            if node is not None:
                if node.tag == 'ul':
                    ul = node
                if node.tag == 'li' and len(node.getchildren()) == 1 and node.getchildren()[0].tag == 'ul':
                    ul = node.getchildren()[0]

            if ul is not None:
                for child in ul.getchildren():
                    if child.tag == 'li':
                        self._update_checklist_recursive(child, checked, children=True)

        # propagate to ancestors
        if ancestors:
            allSelected = True
            ul = li.getparent()
            if ul.tag == 'li':
                ul = ul.getparent()

            for child in ul.getchildren():
                if child.tag == 'li' and 'o_checked' not in child.get('class', ''):
                    allSelected = False

            node = ul.getprevious()
            if node is not None and node.tag == 'li':
                self._update_checklist_recursive(node, allSelected, ancestors=True)

        return True

    #------------------------------------------------------
    # upload an image as base64
    #------------------------------------------------------
    @http.route('/web_editor/add_image_base64', type='json', auth='user', methods=['POST'], website=True)
    def add_image_base64(self, res_model, res_id, image_base64, filename, disable_optimization=None, **kwargs):
        data = base64.b64decode(image_base64)
        attachment = self._image_to_attachment(res_model, res_id, data, filename, filename, disable_optimization=disable_optimization)
        return attachment.read(['name', 'mimetype', 'checksum', 'url', 'res_id', 'res_model', 'access_token'])[0]

    def _check_image_to_attachment(self, data, disable_optimization):
        try:
            image = Image.open(io.BytesIO(data))
            w, h = image.size
            if w*h > 42e6: # Nokia Lumia 1020 photo resolution
                raise ValueError(
                    u"Image size excessive, uploaded images must be smaller "
                    u"than 42 million pixel")
            if not disable_optimization and image.format in ('PNG', 'JPEG'):
                return tools.image_save_for_web(image)
        except IOError:
            pass

    def _image_to_attachment(self, res_model, res_id, data, name, datas_fname, disable_optimization=None):
        Attachments = request.env['ir.attachment']
        data = self._check_image_to_attachment(data, disable_optimization) or data
        attachment = Attachments.create({
            'name': name,
            'datas_fname': datas_fname,
            'datas': base64.b64encode(data),
            'public': res_model == 'ir.ui.view',
            'res_id': res_id,
            'res_model': res_model,
        })
        attachment.generate_access_token()
        return attachment

    #------------------------------------------------------
    # add attachment (images or link)
    #------------------------------------------------------
    @http.route('/web_editor/attachment/add', type='http', auth='user', methods=['POST'], website=True)
    def attach(self, upload=None, url=None, disable_optimization=None, filters=None, **kwargs):
        # the upload argument doesn't allow us to access the files if more than
        # one file is uploaded, as upload references the first file
        # therefore we have to recover the files from the request object
        Attachments = request.env['ir.attachment']  # registry for the attachment table

        res_model = kwargs.get('res_model', 'ir.ui.view')
        if res_model != 'ir.ui.view' and kwargs.get('res_id'):
            res_id = int(kwargs['res_id'])
        else:
            res_id = None

        uploads = []
        message = None
        if not upload: # no image provided, storing the link and the image name
            name = url.split("/").pop()                       # recover filename
            datas_fname = name
            if filters:
                datas_fname = filters + '_' + datas_fname
            attachment = Attachments.create({
                'name': name,
                'datas_fname': datas_fname,
                'type': 'url',
                'url': url,
                'public': res_model == 'ir.ui.view',
                'res_id': res_id,
                'res_model': res_model,
            })
            attachment.generate_access_token()
            uploads += attachment.read(['name', 'mimetype', 'checksum', 'url', 'res_id', 'res_model', 'access_token'])
        else:                                                  # images provided
            try:
                attachments = request.env['ir.attachment']
                for c_file in request.httprequest.files.getlist('upload'):
                    data = c_file.read()
                    name = c_file.filename
                    datas_fname = name
                    if filters:
                        datas_fname = filters + '_' + datas_fname
                    attachments += self._image_to_attachment(res_model, res_id, data, name, datas_fname, disable_optimization=disable_optimization)
                uploads += attachments.read(['name', 'mimetype', 'checksum', 'url', 'res_id', 'res_model', 'access_token'])
            except Exception as e:
                logger.exception("Failed to upload image to attachment")
                message = str(e)

        return """<script type='text/javascript'>
            window.attachments = %s;
            window.error = %s;
        </script>""" % (json.dumps(uploads), json.dumps(message))

    #------------------------------------------------------
    # remove attachment (images or link)
    #------------------------------------------------------
    @http.route('/web_editor/attachment/remove', type='json', auth='user', website=True)
    def remove(self, ids, **kwargs):
        """ Removes a web-based image attachment if it is used by no view (template)

        Returns a dict mapping attachments which would not be removed (if any)
        mapped to the views preventing their removal
        """
        Attachment = attachments_to_remove = request.env['ir.attachment']
        Views = request.env['ir.ui.view']

        # views blocking removal of the attachment
        removal_blocked_by = {}

        for attachment in Attachment.browse(ids):
            # in-document URLs are html-escaped, a straight search will not
            # find them
            url = tools.html_escape(attachment.local_url)
            views = Views.search([
                "|",
                ('arch_db', 'like', '"%s"' % url),
                ('arch_db', 'like', "'%s'" % url)
            ])

            if views:
                removal_blocked_by[attachment.id] = views.read(['name'])
            else:
                attachments_to_remove += attachment
        if attachments_to_remove:
            attachments_to_remove.unlink()
        return removal_blocked_by

    ## This route is used from CropImageDialog to get image info.
    ## It is used to display the original image when we crop a previously
    ## cropped image
    @http.route('/web_editor/get_image_info', type='json', auth='user', website=True)
    def get_image_info(self, image_id=None, xml_id=None):
        if xml_id:
            record = request.env['ir.attachment'].get_attachment_by_key(xml_id)
        elif image_id:
            record = request.env['ir.attachment'].browse(image_id)
        result = {
            'mimetype': record.mimetype,
        }
        # If we received the image ID and that image has an associated URL
        # field, this should be a crop image attachment, so we return the ID
        # and URL to confirm
        if image_id and record.url:
            result['id'] = record.id
            result['originalSrc'] = record.url
        return result

    @http.route("/web_editor/get_assets_editor_resources", type="json", auth="user", website=True)
    def get_assets_editor_resources(self, key, get_views=True, get_scss=True, get_js=True, bundles=False, bundles_restriction=[], only_user_custom_files=True):
        """
        Transmit the resources the assets editor needs to work.

        Params:
            key (str): the key of the view the resources are related to

            get_views (bool, default=True):
                True if the views must be fetched

            get_scss (bool, default=True):
                True if the style must be fetched

            get_js (bool, default=True):
                True if the javascript must be fetched

            bundles (bool, default=False):
                True if the bundles views must be fetched

            bundles_restriction (list, default=[]):
                Names of the bundles in which to look for scss files
                (if empty, search in all of them)

            only_user_custom_files (bool, default=True):
                True if only user custom files must be fetched

        Returns:
            dict: views, scss, js
        """
        # Related views must be fetched if the user wants the views and/or the style
        views = request.env["ir.ui.view"].get_related_views(key, bundles=bundles)
        views = views.read(['name', 'id', 'key', 'xml_id', 'arch', 'active', 'inherit_id'])

        scss_files_data_by_bundle = []
        js_files_data_by_bundle = []

        if get_scss:
            scss_files_data_by_bundle = self._load_resources('scss', views, bundles_restriction, only_user_custom_files)
        if get_js:
            js_files_data_by_bundle = self._load_resources('js', views, bundles_restriction, only_user_custom_files)

        return {
            'views': get_views and views or [],
            'scss': get_scss and scss_files_data_by_bundle or [],
            'js': get_js and js_files_data_by_bundle or [],
        }

    def _load_resources(self, file_type, views, bundles_restriction, only_user_custom_files):
        AssetsUtils = request.env['web_editor.assets']

        files_data_by_bundle = []
        resources_type_info = {'t_call_assets_attribute': 't-js', 'mimetype': 'text/javascript'}
        if file_type == 'scss':
            resources_type_info = {'t_call_assets_attribute': 't-css', 'mimetype': 'text/scss'}

        # Compile regex outside of the loop
        # This will used to exclude library scss files from the result
        excluded_url_matcher = re.compile("^(.+/lib/.+)|(.+import_bootstrap.+\.scss)$")

        # First check the t-call-assets used in the related views
        url_infos = dict()
        for v in views:
            for asset_call_node in etree.fromstring(v["arch"]).xpath("//t[@t-call-assets]"):
                if asset_call_node.get(resources_type_info['t_call_assets_attribute']) == "false":
                    continue
                asset_name = asset_call_node.get("t-call-assets")

                # Loop through bundle files to search for file info
                files_data = []
                for file_info in request.env["ir.qweb"]._get_asset_content(asset_name, {})[0]:
                    if file_info["atype"] != resources_type_info['mimetype']:
                        continue
                    url = file_info["url"]

                    # Exclude library files (see regex above)
                    if excluded_url_matcher.match(url):
                        continue

                    # Check if the file is customized and get bundle/path info
                    file_data = AssetsUtils.get_asset_info(url)
                    if not file_data:
                        continue

                    # Save info according to the filter (arch will be fetched later)
                    url_infos[url] = file_data

                    if '/user_custom_' in url \
                            or file_data['customized'] \
                            or file_type == 'scss' and not only_user_custom_files:
                        files_data.append(url)

                # scss data is returned sorted by bundle, with the bundles
                # names and xmlids
                if len(files_data):
                    files_data_by_bundle.append([
                        {'xmlid': asset_name, 'name': request.env.ref(asset_name).name},
                        files_data
                    ])

        # Filter bundles/files:
        # - A file which appears in multiple bundles only appears in the
        #   first one (the first in the DOM)
        # - Only keep bundles with files which appears in the asked bundles
        #   and only keep those files
        for i in range(0, len(files_data_by_bundle)):
            bundle_1 = files_data_by_bundle[i]
            for j in range(0, len(files_data_by_bundle)):
                bundle_2 = files_data_by_bundle[j]
                # In unwanted bundles, keep only the files which are in wanted bundles too (_assets_helpers)
                if bundle_1[0]["xmlid"] not in bundles_restriction and bundle_2[0]["xmlid"] in bundles_restriction:
                    bundle_1[1] = [item_1 for item_1 in bundle_1[1] if item_1 in bundle_2[1]]
        for i in range(0, len(files_data_by_bundle)):
            bundle_1 = files_data_by_bundle[i]
            for j in range(i + 1, len(files_data_by_bundle)):
                bundle_2 = files_data_by_bundle[j]
                # In every bundle, keep only the files which were not found
                # in previous bundles
                bundle_2[1] = [item_2 for item_2 in bundle_2[1] if item_2 not in bundle_1[1]]

        # Only keep bundles which still have files and that were requested
        files_data_by_bundle = [
            data for data in files_data_by_bundle
            if (len(data[1]) > 0 and (not bundles_restriction or data[0]["xmlid"] in bundles_restriction))
        ]

        # Fetch the arch of each kept file, in each bundle
        urls = []
        for bundle_data in files_data_by_bundle:
            urls += bundle_data[1]
        custom_attachments = AssetsUtils.get_all_custom_attachments(urls)

        for bundle_data in files_data_by_bundle:
            for i in range(0, len(bundle_data[1])):
                url = bundle_data[1][i]
                url_info = url_infos[url]

                content = AssetsUtils.get_asset_content(url, url_info, custom_attachments)

                bundle_data[1][i] = {
                    'url': "/%s/%s" % (url_info["module"], url_info["resource_path"]),
                    'arch': content,
                    'customized': url_info["customized"],
                }

        return files_data_by_bundle

    @http.route("/web_editor/save_asset", type="json", auth="user", website=True)
    def save_asset(self, url, bundle_xmlid, content, file_type):
        """
        Save a given modification of a scss/js file.

        Params:
            url (str):
                the original url of the scss/js file which has to be modified

            bundle_xmlid (str):
                the xmlid of the bundle in which the scss/js file addition can
                be found

            content (str): the new content of the scss/js file

            file_type (str): 'scss' or 'js'
        """
        request.env['web_editor.assets'].save_asset(url, bundle_xmlid, content, file_type)

    @http.route("/web_editor/reset_asset", type="json", auth="user", website=True)
    def reset_asset(self, url, bundle_xmlid):
        """
        The reset_asset route is in charge of reverting all the changes that
        were done to a scss/js file.

        Params:
            url (str):
                the original URL of the scss/js file to reset

            bundle_xmlid (str):
                the xmlid of the bundle in which the scss/js file addition can
                be found
        """
        request.env['web_editor.assets'].reset_asset(url, bundle_xmlid)
