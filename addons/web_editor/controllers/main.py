# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json
import logging
import re
import time
import requests
import werkzeug.exceptions
import werkzeug.urls
from PIL import Image, ImageFont, ImageDraw
from lxml import etree
from base64 import b64decode, b64encode
from math import floor
from os.path import join as opj

from odoo.http import request, Response
from odoo import http, tools, _
from odoo.tools.misc import file_open
from odoo.tools.image import image_data_uri, binary_to_image, get_webp_size


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
    def export_icon_to_png(self, icon, color='#000', bg=None, size=100, alpha=255, font='/web/static/src/libs/fontawesome/fonts/fontawesome-webfont.ttf', width=None, height=None):
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
        # For custom icons, use the corresponding custom font
        if icon.isdigit():
            if int(icon) == 57467:
                font = "/web/static/fonts/tiktok_only.woff"
            elif int(icon) == 61593:  # F099
                icon = "59392"  # E800
                font = "/web/static/fonts/twitter_x_only.woff"
            elif int(icon) == 61569:  # F081
                icon = "59395"  # E803
                font = "/web/static/fonts/twitter_x_only.woff"

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

        # Convert the opacity value compatible with PIL Image color (0 to 255)
        # when color specifier is 'rgba'
        if color is not None and color.startswith('rgba'):
            *rgb, a = color.strip(')').split(',')
            opacity = str(floor(float(a) * 255))
            color = ','.join([*rgb, opacity]) + ')'

        # Determine the dimensions of the icon
        image = Image.new("RGBA", (width, height), color)
        draw = ImageDraw.Draw(image)

        if hasattr(draw, 'textbbox'):
            box = draw.textbbox((0, 0), icon, font=font_obj)
            left = box[0]
            top = box[1]
            boxw = box[2] - box[0]
            boxh = box[3] - box[1]
        else:  # pillow < 8.00 (Focal)
            left, top, _right, _bottom = image.getbbox()
            boxw, boxh = draw.textsize(icon, font=font_obj)

        draw.text((0, 0), icon, font=font_obj)

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
        response = Response()
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

    @http.route('/web_editor/attachment/remove', type='jsonrpc', auth='user', website=True)
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


    def _clean_context(self):
        # avoid allowed_company_ids which may erroneously restrict based on website
        context = dict(request.context)
        context.pop('allowed_company_ids', None)
        request.update_env(context=context)

    @http.route("/web_editor/get_assets_editor_resources", type="jsonrpc", auth="user", website=True)
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
        t_call_assets_attribute = 't-js'
        if file_type == 'scss':
            t_call_assets_attribute = 't-css'

        # Compile regex outside of the loop
        # This will used to exclude library scss files from the result
        excluded_url_matcher = re.compile(r"^(.+/lib/.+)|(.+import_bootstrap.+\.scss)$")

        # First check the t-call-assets used in the related views
        url_infos = dict()
        for v in views:
            for asset_call_node in etree.fromstring(v["arch"]).xpath("//t[@t-call-assets]"):
                attr = asset_call_node.get(t_call_assets_attribute)
                if attr and not json.loads(attr.lower()):
                    continue
                asset_name = asset_call_node.get("t-call-assets")

                # Loop through bundle files to search for file info
                files_data = []
                for file_info in request.env["ir.qweb"]._get_asset_content(asset_name)[0]:
                    if file_info["url"].rpartition('.')[2] != file_type:
                        continue
                    url = file_info["url"]

                    # Exclude library files (see regex above)
                    if excluded_url_matcher.match(url):
                        continue

                    # Check if the file is customized and get bundle/path info
                    file_data = AssetsUtils._get_data_from_url(url)
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
        custom_attachments = AssetsUtils._get_custom_attachment(urls, op='in')

        for bundle_data in files_data_by_bundle:
            for i in range(0, len(bundle_data[1])):
                url = bundle_data[1][i]
                url_info = url_infos[url]

                content = AssetsUtils._get_content_from_url(url, url_info, custom_attachments)

                bundle_data[1][i] = {
                    'url': "/%s/%s" % (url_info["module"], url_info["resource_path"]),
                    'arch': content,
                    'customized': url_info["customized"],
                }

        return files_data_by_bundle

    def _get_shape_svg(self, module, *segments):
        Module = request.env['ir.module.module'].sudo()
        # Avoid creating a bridge module just for this check.
        if 'imported' in Module._fields and Module.search([('name', '=', module)]).imported:
            attachment = request.env['ir.attachment'].sudo().search([
                ('url', '=', f"/{module.replace('.', '_')}/static/{'/'.join(segments)}"),
                ('public', '=', True),
                ('type', '=', 'binary'),
            ], limit=1)
            if attachment:
                return b64decode(attachment.datas)
            raise werkzeug.exceptions.NotFound()
        shape_path = opj(module, 'static', *segments)
        try:
            with file_open(shape_path, 'r', filter_ext=('.svg',)) as file:
                return file.read()
        except FileNotFoundError:
            raise werkzeug.exceptions.NotFound()

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
        regex_rgba = r'rgba?\(\d{1,3}, ?\d{1,3}, ?\d{1,3}(?:, ?[0-9.]{1,4})?\)'
        for key, value in options.items():
            colorMatch = re.match('^c([1-5])$', key)
            if colorMatch:
                css_color_value = value
                # Check that color is hex or rgb(a) to prevent arbitrary injection
                if not re.match(r'(?i)^%s$|^%s$' % (regex_hex, regex_rgba), css_color_value.replace(' ', '')):
                    if re.match('^o-color-([1-5])$', css_color_value):
                        if not bundle_css:
                            bundle = 'web.assets_frontend'
                            asset = request.env["ir.qweb"]._get_asset_bundle(bundle)
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

    @http.route(['/web_editor/image_shape/<string:img_key>/<module>/<path:filename>'], type='http', auth="public", website=True)
    def image_shape(self, module, filename, img_key, **kwargs):
        svg = self._get_shape_svg(module, 'image_shapes', filename)

        record = request.env['ir.binary']._find_record(img_key)
        stream = request.env['ir.binary']._get_image_stream_from(record)
        if stream.type == 'url':
            return stream.get_response()

        image = stream.read()
        if record.mimetype == "image/webp":
            width, height = tuple(str(size) for size in get_webp_size(image))
        else:
            img = binary_to_image(image)
            width, height = tuple(str(size) for size in img.size)
        root = etree.fromstring(svg)

        if root.attrib.get("data-forced-size"):
            # Adjusts the SVG height to ensure the image fits properly within
            # the SVG (e.g. for "devices" shapes).
            svgHeight = float(root.attrib.get("height"))
            svgWidth = float(root.attrib.get("width"))
            svgAspectRatio = svgWidth / svgHeight
            height = str(float(width) / svgAspectRatio)

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

    @http.route(['/web_editor/media_library_search'], type='jsonrpc', auth="user", website=True)
    def media_library_search(self, **params):
        ICP = request.env['ir.config_parameter'].sudo()
        endpoint = ICP.get_param('web_editor.media_library_endpoint', DEFAULT_LIBRARY_ENDPOINT)
        params['dbuuid'] = ICP.get_param('database.uuid')
        response = requests.post('%s/media-library/1/search' % endpoint, data=params)
        if response.status_code == requests.codes.ok and response.headers['content-type'] == 'application/json':
            return response.json()
        else:
            return {'error': response.status_code}

    @http.route('/web_editor/tests', type='http', auth="user")
    def test_suite(self, mod=None, **kwargs):
        return request.render('web_editor.tests')

    @http.route("/web_editor/field/translation/update", type="jsonrpc", auth="user", website=True)
    def update_field_translation(self, model, record_id, field_name, translations):
        record = request.env[model].browse(record_id)
        return record.web_update_field_translations(field_name, translations)
