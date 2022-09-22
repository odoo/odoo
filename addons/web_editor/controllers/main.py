# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json
import logging
import re
import time
import requests
import werkzeug.urls
import werkzeug.wrappers
from PIL import Image, ImageFont, ImageDraw
from lxml import etree
from base64 import b64decode, b64encode

from odoo.http import request
from odoo import http, tools, _, SUPERUSER_ID
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.web_editor.tools import get_video_url_data
from odoo.exceptions import UserError
from odoo.modules.module import get_resource_path
from odoo.tools import file_open
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.image import image_data_uri, binary_to_image
from odoo.addons.base.models.assetsbundle import AssetsBundle

from ..models.ir_attachment import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_IMAGE_MIMETYPES

logger = logging.getLogger(__name__)
DEFAULT_LIBRARY_ENDPOINT = 'https://media-api.odoo.com'

class Web_Editor(http.Controller):
    #------------------------------------------------------
    # convert font into picture
    #------------------------------------------------------
    @http.route([
        '/web_editor/font_to_img/<icon>',
        '/web_editor/font_to_img/<icon>/<color>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>',
        '/web_editor/font_to_img/<icon>/<color>/<int:width>x<int:height>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        '/web_editor/font_to_img/<icon>/<color>/<int:width>x<int:height>/<int:alpha>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>/<int:size>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>/<int:alpha>',
        ], type='http', auth="none")
    def export_icon_to_png(self, icon, color='#000', bg=None, size=100, alpha=255, font='/web/static/lib/fontawesome/fonts/fontawesome-webfont.ttf', width=None, height=None):
        """ This method converts an unicode character to an image (using Font
            Awesome font by default) and is used only for mass mailing because
            custom fonts are not supported in mail.
            :param icon : decimal encoding of unicode character
            :param color : RGB code of the color
            :param bg : RGB code of the background color
            :param size : Pixels in integer
            :param alpha : transparency of the image from 0 to 255
            :param font : font path
            :param width : Pixels in integer
            :param height : Pixels in integer

            :returns PNG image converted from given font
        """
        size = max(width, height, 1) if width else size
        width = width or size
        height = height or size
        # Make sure we have at least size=1
        width = max(1, min(width, 512))
        height = max(1, min(height, 512))
        # Initialize font
        if font.startswith('/'):
            font = font[1:]
        font_obj = ImageFont.truetype(file_open(font, 'rb'), height)

        # if received character is not a number, keep old behaviour (icon is character)
        icon = chr(int(icon)) if icon.isdigit() else icon

        # Background standardization
        if bg is not None and bg.startswith('rgba'):
            bg = bg.replace('rgba', 'rgb')
            bg = ','.join(bg.split(',')[:-1])+')'

        # Determine the dimensions of the icon
        image = Image.new("RGBA", (width, height), color)
        draw = ImageDraw.Draw(image)

        boxw, boxh = draw.textsize(icon, font=font_obj)
        draw.text((0, 0), icon, font=font_obj)
        left, top, right, bottom = image.getbbox()

        # Create an alpha mask
        imagemask = Image.new("L", (boxw, boxh), 0)
        drawmask = ImageDraw.Draw(imagemask)
        drawmask.text((-left, -top), icon, font=font_obj, fill=255)

        # Create a solid color image and apply the mask
        if color.startswith('rgba'):
            color = color.replace('rgba', 'rgb')
            color = ','.join(color.split(',')[:-1])+')'
        iconimage = Image.new("RGBA", (boxw, boxh), color)
        iconimage.putalpha(imagemask)

        # Create output image
        outimage = Image.new("RGBA", (boxw, height), bg or (0, 0, 0, 0))
        outimage.paste(iconimage, (left, top), iconimage)

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

        value = etree.tostring(htmlelem[0][0], encoding='utf-8', method='html')[5:-6]
        record.write({filename: value})

        return value

    #------------------------------------------------------
    # Update a stars rating in the editor on check/uncheck
    #------------------------------------------------------
    @http.route('/web_editor/stars', type='json', auth='user')
    def update_stars(self, res_model, res_id, filename, starsId, rating):
        record = request.env[res_model].browse(res_id)
        value = getattr(record, filename, False)
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

    @http.route('/web_editor/video_url/data', type='json', auth='user', website=True)
    def video_url_data(self, video_url, autoplay=False, loop=False,
                       hide_controls=False, hide_fullscreen=False, hide_yt_logo=False,
                       hide_dm_logo=False, hide_dm_share=False):
        if not request.env.user.has_group('base.group_user'):
            raise werkzeug.exceptions.Forbidden()
        return get_video_url_data(
            video_url, autoplay=autoplay, loop=loop,
            hide_controls=hide_controls, hide_fullscreen=hide_fullscreen,
            hide_yt_logo=hide_yt_logo, hide_dm_logo=hide_dm_logo,
            hide_dm_share=hide_dm_share
        )

    @http.route('/web_editor/attachment/add_data', type='json', auth='user', methods=['POST'], website=True)
    def add_data(self, name, data, is_image, quality=0, width=0, height=0, res_id=False, res_model='ir.ui.view', generate_access_token=False, **kwargs):
        data = b64decode(data)
        if is_image:
            format_error_msg = _("Uploaded image's format is not supported. Try with: %s", ', '.join(SUPPORTED_IMAGE_EXTENSIONS))
            try:
                data = tools.image_process(data, size=(width, height), quality=quality, verify_resolution=True)
                mimetype = guess_mimetype(data)
                if mimetype not in SUPPORTED_IMAGE_MIMETYPES:
                    return {'error': format_error_msg}
            except UserError:
                # considered as an image by the browser file input, but not
                # recognized as such by PIL, eg .webp
                return {'error': format_error_msg}
            except ValueError as e:
                return {'error': e.args[0]}

        self._clean_context()
        attachment = self._attachment_create(name=name, data=data, res_id=res_id, res_model=res_model, generate_access_token=generate_access_token)
        return attachment._get_media_info()

    @http.route('/web_editor/attachment/add_url', type='json', auth='user', methods=['POST'], website=True)
    def add_url(self, url, res_id=False, res_model='ir.ui.view', **kwargs):
        self._clean_context()
        attachment = self._attachment_create(url=url, res_id=res_id, res_model=res_model)
        return attachment._get_media_info()

    @http.route('/web_editor/attachment/remove', type='json', auth='user', website=True)
    def remove(self, ids, **kwargs):
        """ Removes a web-based image attachment if it is used by no view (template)

        Returns a dict mapping attachments which would not be removed (if any)
        mapped to the views preventing their removal
        """
        self._clean_context()
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

    @http.route('/web_editor/get_image_info', type='json', auth='user', website=True)
    def get_image_info(self, src=''):
        """This route is used to determine the original of an attachment so that
        it can be used as a base to modify it again (crop/optimization/filters).
        """
        attachment = None
        id_match = re.search('^/web/image/([^/?]+)', src)
        if id_match:
            url_segment = id_match.group(1)
            number_match = re.match('^(\d+)', url_segment)
            if '.' in url_segment: # xml-id
                attachment = request.env['ir.http']._xmlid_to_obj(request.env, url_segment)
            elif number_match: # numeric id
                attachment = request.env['ir.attachment'].browse(int(number_match.group(1)))
        else:
            # Find attachment by url. There can be multiple matches because of default
            # snippet images referencing the same image in /static/, so we limit to 1
            attachment = request.env['ir.attachment'].search([
                '|', ('url', '=like', src), ('url', '=like', '%s?%%' % src),
                ('mimetype', 'in', SUPPORTED_IMAGE_MIMETYPES),
            ], limit=1)
        if not attachment:
            return {
                'attachment': False,
                'original': False,
            }
        return {
            'attachment': attachment.read(['id'])[0],
            'original': (attachment.original_id or attachment).read(['id', 'image_src', 'mimetype'])[0],
        }

    def _attachment_create(self, name='', data=False, url=False, res_id=False, res_model='ir.ui.view', generate_access_token=False):
        """Create and return a new attachment."""
        if name.lower().endswith('.bmp'):
            # Avoid mismatch between content type and mimetype, see commit msg
            name = name[:-4]

        if not name and url:
            name = url.split("/").pop()

        if res_model != 'ir.ui.view' and res_id:
            res_id = int(res_id)
        else:
            res_id = False

        attachment_data = {
            'name': name,
            'public': res_model == 'ir.ui.view',
            'res_id': res_id,
            'res_model': res_model,
        }

        if data:
            attachment_data['raw'] = data
        elif url:
            attachment_data.update({
                'type': 'url',
                'url': url,
            })
        else:
            raise UserError(_("You need to specify either data or url to create an attachment."))

        attachment = request.env['ir.attachment'].create(attachment_data)
        if generate_access_token:
            attachment.generate_access_token()

        return attachment

    def _clean_context(self):
        # avoid allowed_company_ids which may erroneously restrict based on website
        context = dict(request.context)
        context.pop('allowed_company_ids', None)
        request.context = context

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
        views = request.env["ir.ui.view"].with_context(no_primary_children=True, __views_get_original_hierarchy=[]).get_related_views(key, bundles=bundles)
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
                attr = asset_call_node.get(resources_type_info['t_call_assets_attribute'])
                if attr and not json.loads(attr.lower()):
                    continue
                asset_name = asset_call_node.get("t-call-assets")

                # Loop through bundle files to search for file info
                files_data = []
                for file_info in request.env["ir.qweb"]._get_asset_content(asset_name)[0]:
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
                    files_data_by_bundle.append([asset_name, files_data])

        # Filter bundles/files:
        # - A file which appears in multiple bundles only appears in the
        #   first one (the first in the DOM)
        # - Only keep bundles with files which appears in the asked bundles
        #   and only keep those files
        for i in range(0, len(files_data_by_bundle)):
            bundle_1 = files_data_by_bundle[i]
            for j in range(0, len(files_data_by_bundle)):
                bundle_2 = files_data_by_bundle[j]
                # In unwanted bundles, keep only the files which are in wanted bundles too (web._helpers)
                if bundle_1[0] not in bundles_restriction and bundle_2[0] in bundles_restriction:
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
            if (len(data[1]) > 0 and (not bundles_restriction or data[0] in bundles_restriction))
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
    def save_asset(self, url, bundle, content, file_type):
        """
        Save a given modification of a scss/js file.

        Params:
            url (str):
                the original url of the scss/js file which has to be modified

            bundle (str):
                the name of the bundle in which the scss/js file addition can
                be found

            content (str): the new content of the scss/js file

            file_type (str): 'scss' or 'js'
        """
        request.env['web_editor.assets'].save_asset(url, bundle, content, file_type)

    @http.route("/web_editor/reset_asset", type="json", auth="user", website=True)
    def reset_asset(self, url, bundle):
        """
        The reset_asset route is in charge of reverting all the changes that
        were done to a scss/js file.

        Params:
            url (str):
                the original URL of the scss/js file to reset

            bundle (str):
                the name of the bundle in which the scss/js file addition can
                be found
        """
        request.env['web_editor.assets'].reset_asset(url, bundle)

    @http.route("/web_editor/public_render_template", type="json", auth="public", website=True)
    def public_render_template(self, args):
        # args[0]: xml id of the template to render
        # args[1]: optional dict of rendering values, only trusted keys are supported
        len_args = len(args)
        assert len_args >= 1 and len_args <= 2, 'Need a xmlID and potential rendering values to render a template'

        trusted_value_keys = ('debug',)

        xmlid = args[0]
        values = len_args > 1 and args[1] or {}

        View = request.env['ir.ui.view']
        return View.render_public_asset(xmlid, {k: values[k] for k in values if k in trusted_value_keys})

    @http.route('/web_editor/modify_image/<model("ir.attachment"):attachment>', type="json", auth="user", website=True)
    def modify_image(self, attachment, res_model=None, res_id=None, name=None, data=None, original_id=None, mimetype=None):
        """
        Creates a modified copy of an attachment and returns its image_src to be
        inserted into the DOM.
        """
        fields = {
            'original_id': attachment.id,
            'datas': data,
            'type': 'binary',
            'res_model': res_model or 'ir.ui.view',
            'mimetype': mimetype or attachment.mimetype,
        }
        if fields['res_model'] == 'ir.ui.view':
            fields['res_id'] = 0
        elif res_id:
            fields['res_id'] = res_id
        if name:
            fields['name'] = name
        attachment = attachment.copy(fields)
        if attachment.url:
            # Don't keep url if modifying static attachment because static images
            # are only served from disk and don't fallback to attachments.
            if re.match(r'^/\w+/static/', attachment.url):
                attachment.url = None
            # Uniquify url by adding a path segment with the id before the name.
            # This allows us to keep the unsplash url format so it still reacts
            # to the unsplash beacon.
            else:
                url_fragments = attachment.url.split('/')
                url_fragments.insert(-1, str(attachment.id))
                attachment.url = '/'.join(url_fragments)
        if attachment.public:
            return attachment.image_src
        attachment.generate_access_token()
        return '%s?access_token=%s' % (attachment.image_src, attachment.access_token)

    def _get_shape_svg(self, module, *segments):
        shape_path = get_resource_path(module, 'static', *segments)
        if not shape_path:
            raise werkzeug.exceptions.NotFound()
        with tools.file_open(shape_path, 'r', filter_ext=('.svg',)) as file:
            return file.read()

    def _update_svg_colors(self, options, svg):
        user_colors = []
        svg_options = {}
        default_palette = {
            '1': '#3AADAA',
            '2': '#7C6576',
            '3': '#F6F6F6',
            '4': '#FFFFFF',
            '5': '#383E45',
        }
        bundle_css = None
        regex_hex = r'#[0-9A-F]{6,8}'
        regex_rgba = r'rgba?\(\d{1,3},\d{1,3},\d{1,3}(?:,[0-9.]{1,4})?\)'
        for key, value in options.items():
            colorMatch = re.match('^c([1-5])$', key)
            if colorMatch:
                css_color_value = value
                # Check that color is hex or rgb(a) to prevent arbitrary injection
                if not re.match(r'(?i)^%s$|^%s$' % (regex_hex, regex_rgba), css_color_value.replace(' ', '')):
                    if re.match('^o-color-([1-5])$', css_color_value):
                        if not bundle_css:
                            bundle = 'web.assets_frontend'
                            files, _ = request.env["ir.qweb"]._get_asset_content(bundle)
                            asset = AssetsBundle(bundle, files)
                            bundle_css = asset.css().index_content
                        color_search = re.search(r'(?i)--%s:\s+(%s|%s)' % (css_color_value, regex_hex, regex_rgba), bundle_css)
                        if not color_search:
                            raise werkzeug.exceptions.BadRequest()
                        css_color_value = color_search.group(1)
                    else:
                        raise werkzeug.exceptions.BadRequest()
                user_colors.append([tools.html_escape(css_color_value), colorMatch.group(1)])
            else:
                svg_options[key] = value

        color_mapping = {default_palette[palette_number]: color for color, palette_number in user_colors}
        # create a case-insensitive regex to match all the colors to replace, eg: '(?i)(#3AADAA)|(#7C6576)'
        regex = '(?i)%s' % '|'.join('(%s)' % color for color in color_mapping.keys())

        def subber(match):
            key = match.group().upper()
            return color_mapping[key] if key in color_mapping else key
        return re.sub(regex, subber, svg), svg_options

    @http.route(['/web_editor/shape/<module>/<path:filename>'], type='http', auth="public", website=True)
    def shape(self, module, filename, **kwargs):
        """
        Returns a color-customized svg (background shape or illustration).
        """
        svg = None
        if module == 'illustration':
            attachment = request.env['ir.attachment'].sudo().browse(unslug(filename)[1])
            if (not attachment.exists()
                    or attachment.type != 'binary'
                    or not attachment.public
                    or not attachment.url.startswith(request.httprequest.path)):
                # Fallback to URL lookup to allow using shapes that were
                # imported from data files.
                attachment = request.env['ir.attachment'].sudo().search([
                    ('type', '=', 'binary'),
                    ('public', '=', True),
                    ('url', '=', request.httprequest.path),
                ], limit=1)
                if not attachment:
                    raise werkzeug.exceptions.NotFound()
            svg = attachment.raw.decode('utf-8')
        else:
            svg = self._get_shape_svg(module, 'shapes', filename)

        svg, options = self._update_svg_colors(kwargs, svg)
        flip_value = options.get('flip', False)
        if flip_value == 'x':
            svg = svg.replace('<svg ', '<svg style="transform: scaleX(-1);" ')
        elif flip_value == 'y':
            svg = svg.replace('<svg ', '<svg style="transform: scaleY(-1)" ')
        elif flip_value == 'xy':
            svg = svg.replace('<svg ', '<svg style="transform: scale(-1)" ')

        return request.make_response(svg, [
            ('Content-type', 'image/svg+xml'),
            ('Cache-control', 'max-age=%s' % http.STATIC_CACHE_LONG),
        ])

    @http.route(['/web_editor/image_shape/<string:img_key>/<module>/<path:filename>'], type='http', auth="public", website=True)
    def image_shape(self, module, filename, img_key, **kwargs):
        svg = self._get_shape_svg(module, 'image_shapes', filename)
        _, _, image = request.env['ir.http'].binary_content(
            xmlid=img_key, model='ir.attachment', field='datas', default_mimetype='image/png')
        if not image:
            image = request.env['ir.http']._placeholder()
        img = binary_to_image(image)
        width, height = tuple(str(size) for size in img.size)
        root = etree.fromstring(svg)
        root.attrib.update({'width': width, 'height': height})
        # Update default color palette on shape SVG.
        svg, _ = self._update_svg_colors(kwargs, etree.tostring(root, pretty_print=True).decode('utf-8'))
        # Add image in base64 inside the shape.
        uri = image_data_uri(b64encode(image))
        svg = svg.replace('<image xlink:href="', '<image xlink:href="%s' % uri)

        return request.make_response(svg, [
            ('Content-type', 'image/svg+xml'),
            ('Cache-control', 'max-age=%s' % http.STATIC_CACHE_LONG),
        ])

    @http.route(['/web_editor/media_library_search'], type='json', auth="user", website=True)
    def media_library_search(self, **params):
        ICP = request.env['ir.config_parameter'].sudo()
        endpoint = ICP.get_param('web_editor.media_library_endpoint', DEFAULT_LIBRARY_ENDPOINT)
        params['dbuuid'] = ICP.get_param('database.uuid')
        response = requests.post('%s/media-library/1/search' % endpoint, data=params)
        if response.status_code == requests.codes.ok and response.headers['content-type'] == 'application/json':
            return response.json()
        else:
            return {'error': response.status_code}

    @http.route('/web_editor/save_library_media', type='json', auth='user', methods=['POST'])
    def save_library_media(self, media):
        """
        Saves images from the media library as new attachments, making them
        dynamic SVGs if needed.
            media = {
                <media_id>: {
                    'query': 'space separated search terms',
                    'is_dynamic_svg': True/False,
                    'dynamic_colors': maps color names to their color,
                }, ...
            }
        """
        attachments = []
        ICP = request.env['ir.config_parameter'].sudo()
        library_endpoint = ICP.get_param('web_editor.media_library_endpoint', DEFAULT_LIBRARY_ENDPOINT)

        media_ids = ','.join(media.keys())
        params = {
            'dbuuid': ICP.get_param('database.uuid'),
            'media_ids': media_ids,
        }
        response = requests.post('%s/media-library/1/download_urls' % library_endpoint, data=params)
        if response.status_code != requests.codes.ok:
            raise Exception(_("ERROR: couldn't get download urls from media library."))

        for id, url in response.json().items():
            req = requests.get(url)
            name = '_'.join([media[id]['query'], url.split('/')[-1]])
            # Need to bypass security check to write image with mimetype image/svg+xml
            # ok because svgs come from whitelisted origin
            context = {'binary_field_real_user': request.env['res.users'].sudo().browse([SUPERUSER_ID])}
            attachment = request.env['ir.attachment'].sudo().with_context(context).create({
                'name': name,
                'mimetype': req.headers['content-type'],
                'datas': b64encode(req.content),
                'public': True,
                'res_model': 'ir.ui.view',
                'res_id': 0,
            })
            if media[id]['is_dynamic_svg']:
                colorParams = werkzeug.urls.url_encode(media[id]['dynamic_colors'])
                attachment['url'] = '/web_editor/shape/illustration/%s?%s' % (slug(attachment), colorParams)
            attachments.append(attachment._get_media_info())

        return attachments

    @http.route("/web_editor/get_ice_servers", type='json', auth="user")
    def get_ice_servers(self):
        return request.env['mail.ice.server']._get_ice_servers()

    @http.route("/web_editor/bus_broadcast", type="json", auth="user")
    def bus_broadcast(self, model_name, field_name, res_id, bus_data):
        document = request.env[model_name].browse([res_id])

        document.check_access_rights('read')
        document.check_field_access_rights('read', [field_name])
        document.check_access_rule('read')
        document.check_access_rights('write')
        document.check_field_access_rights('write', [field_name])
        document.check_access_rule('write')

        channel = (request.db, 'editor_collaboration', model_name, field_name, int(res_id))
        bus_data.update({'model_name': model_name, 'field_name': field_name, 'res_id': res_id})
        request.env['bus.bus']._sendone(channel, 'editor_collaboration', bus_data)
