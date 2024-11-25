import contextlib
import re
import uuid
from base64 import b64decode
from datetime import datetime
import werkzeug.exceptions
import werkzeug.urls
import requests
from os.path import join as opj

from odoo import _, http, tools, SUPERUSER_ID
from odoo.addons.html_editor.tools import get_video_url_data
from odoo.exceptions import UserError, MissingError, AccessError
from odoo.http import request
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import file_open
from odoo.addons.iap.tools import iap_tools
from odoo.addons.mail.tools import link_preview

from ..models.ir_attachment import SUPPORTED_IMAGE_MIMETYPES

DEFAULT_LIBRARY_ENDPOINT = 'https://media-api.odoo.com'
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'

# Regex definitions to apply speed modification in SVG files
# Note : These regex patterns are duplicated on the server side for
# background images that are part of a CSS rule "background-image: ...". The
# client-side regex patterns are used for images that are part of an
# "src" attribute with a base64 encoded svg in the <img> tag. Perhaps we should
# consider finding a solution to define them only once? The issue is that the
# regex patterns in Python are slightly different from those in JavaScript.

CSS_ANIMATION_RULE_REGEX = (
        r"(?P<declaration>animation(-duration)?: .*?)"
        + r"(?P<value>(\d+(\.\d+)?)|(\.\d+))"
        + r"(?P<unit>ms|s)"
        + r"(?P<separator>\s|;|\"|$)"
)
SVG_DUR_TIMECOUNT_VAL_REGEX = (
        r"(?P<attribute_name>\sdur=\"\s*)"
        + r"(?P<value>(\d+(\.\d+)?)|(\.\d+))"
        + r"(?P<unit>h|min|ms|s)?\s*\""
)
CSS_ANIMATION_RATIO_REGEX = (
    r"(--animation_ratio: (?P<ratio>\d*(\.\d+)?));"
)


def _get_shape_svg(self, module, *segments):
    shape_path = opj(module, 'static', *segments)
    try:
        with file_open(shape_path, 'r', filter_ext=('.svg',)) as file:
            return file.read()
    except FileNotFoundError:
        raise werkzeug.exceptions.NotFound()


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


class HTML_Editor(http.Controller):

    def _get_shape_svg(self, module, *segments):
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

    def replace_animation_duration(self,
                                   shape_animation_speed: float,
                                   svg: str):
        """
        Replace animation durations in SVG and CSS with modified values.

        This function takes a speed value and an SVG string containing
        animations. It uses regular expressions to find and replace the
        duration values in both CSS animation rules and SVG duration attributes
        based on the provided speed.

        Parameters:
            - speed (float): The speed used to calculate the new animation
            durations.
            - svg (str): The SVG string containing animations.

        Returns:
        str: The modified SVG string with updated animation durations.
        """
        ratio = (1 + shape_animation_speed
                 if shape_animation_speed >= 0
                 else 1 / (1 - shape_animation_speed))

        def callback_css_animation_rule(match):
            # Extracting matched groups.
            declaration, value, unit, separator = (
                match.group("declaration"),
                match.group("value"),
                match.group("unit"),
                match.group("separator"),
            )
            # Calculating new animation duration based on ratio.
            value = str(float(value) / (ratio or 1))
            # Constructing and returning the modified CSS animation rule.
            return f"{declaration}{value}{unit}{separator}"

        def callback_svg_dur_timecount_val(match):
            attribute_name, value, unit = (
                match.group("attribute_name"),
                match.group("value"),
                match.group("unit"),
            )
            # Calculating new duration based on ratio.
            value = str(float(value) / (ratio or 1))
            # Constructing and returning the modified SVG duration attribute.
            return f'{attribute_name}{value}{unit or "s"}"'

        def callback_css_animation_ratio(match):
            ratio = match.group("ratio")
            return f'--animation_ratio: {ratio};'

        # Applying regex substitutions to modify animation speed in the
        # 'svg' variable.
        svg = re.sub(
            CSS_ANIMATION_RULE_REGEX,
            callback_css_animation_rule,
            svg
        )
        svg = re.sub(
            SVG_DUR_TIMECOUNT_VAL_REGEX,
            callback_svg_dur_timecount_val,
            svg
        )
        # Create or modify the css variable --animation_ratio for future
        # purpose.
        if re.match(CSS_ANIMATION_RATIO_REGEX, svg):
            svg = re.sub(
                CSS_ANIMATION_RATIO_REGEX,
                callback_css_animation_ratio,
                svg
            )
        else:
            regex = r"<svg .*>"
            declaration = f"--animation-ratio: {ratio}"
            subst = ("\\g<0>\n\t<style>\n\t\t:root { \n\t\t\t" +
                     declaration +
                     ";\n\t\t}\n\t</style>")
            svg = re.sub(regex, subst, svg, flags=re.MULTILINE)
        return svg

    def _clean_context(self):
        # avoid allowed_company_ids which may erroneously restrict based on website
        context = dict(request.context)
        context.pop('allowed_company_ids', None)
        request.update_env(context=context)

    def _attachment_create(self, name='', data=False, url=False, res_id=False, res_model='ir.ui.view'):
        """Create and return a new attachment."""
        IrAttachment = request.env['ir.attachment']

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
            if url:
                attachment_data['url'] = url
        elif url:
            attachment_data.update({
                'type': 'url',
                'url': url,
            })
            # The code issues a HEAD request to retrieve headers from the URL.
            # This approach is beneficial when the URL doesn't conclude with an
            # image extension. By verifying the MIME type, the code ensures that
            # only supported image types are incorporated into the data.
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                mime_type = response.headers['content-type']
                if mime_type in SUPPORTED_IMAGE_MIMETYPES:
                    attachment_data['mimetype'] = mime_type
        else:
            raise UserError(_("You need to specify either data or url to create an attachment."))

        # Despite the user having no right to create an attachment, he can still
        # create an image attachment through some flows
        if (
            not request.env.is_admin()
            and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
        ):
            attachment = IrAttachment.sudo().create(attachment_data)
            # When portal users upload an attachment with the wysiwyg widget,
            # the access token is needed to use the image in the editor. If
            # the attachment is not public, the user won't be able to generate
            # the token, so we need to generate it using sudo
            if not attachment_data['public']:
                attachment.sudo().generate_access_token()
        else:
            attachment = get_existing_attachment(IrAttachment, attachment_data) \
                or IrAttachment.create(attachment_data)

        return attachment

    @http.route(['/web_editor/get_image_info', '/html_editor/get_image_info'], type='jsonrpc', auth='user', website=True)
    def get_image_info(self, src=''):
        """This route is used to determine the information of an attachment so that
        it can be used as a base to modify it again (crop/optimization/filters).
        """
        self._clean_context()
        attachment = None
        if src.startswith('/web/image'):
            with contextlib.suppress(werkzeug.exceptions.NotFound, MissingError):
                _, args = request.env['ir.http']._match(src)
                record = request.env['ir.binary']._find_record(
                    xmlid=args.get('xmlid'),
                    res_model=args.get('model', 'ir.attachment'),
                    res_id=args.get('id'),
                )
                if record._name == 'ir.attachment':
                    attachment = record
        if not attachment:
            # Find attachment by url. There can be multiple matches because of default
            # snippet images referencing the same image in /static/, so we limit to 1
            attachment = request.env['ir.attachment'].search([
                '|', ('url', '=like', src), ('url', '=like', '%s?%%' % src),
                ('mimetype', 'in', list(SUPPORTED_IMAGE_MIMETYPES.keys())),
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

    @http.route(['/web_editor/video_url/data', '/html_editor/video_url/data'], type='jsonrpc', auth='user', website=True)
    def video_url_data(self, video_url, autoplay=False, loop=False,
                       hide_controls=False, hide_fullscreen=False,
                       hide_dm_logo=False, hide_dm_share=False):
        return get_video_url_data(
            video_url, autoplay=autoplay, loop=loop,
            hide_controls=hide_controls, hide_fullscreen=hide_fullscreen,
            hide_dm_logo=hide_dm_logo, hide_dm_share=hide_dm_share
        )

    @http.route(['/web_editor/attachment/add_data', '/html_editor/attachment/add_data'], type='jsonrpc', auth='user', methods=['POST'], website=True)
    def add_data(self, name, data, is_image, quality=0, width=0, height=0, res_id=False, res_model='ir.ui.view', **kwargs):
        data = b64decode(data)
        if is_image:
            format_error_msg = _("Uploaded image's format is not supported. Try with: %s", ', '.join(SUPPORTED_IMAGE_MIMETYPES.values()))
            try:
                data = tools.image_process(data, size=(width, height), quality=quality, verify_resolution=True)
                mimetype = guess_mimetype(data)
                if mimetype not in SUPPORTED_IMAGE_MIMETYPES:
                    return {'error': format_error_msg}
                if not name:
                    name = '%s-%s%s' % (
                        datetime.now().strftime('%Y%m%d%H%M%S'),
                        str(uuid.uuid4())[:6],
                        SUPPORTED_IMAGE_MIMETYPES[mimetype],
                    )
            except UserError:
                # considered as an image by the browser file input, but not
                # recognized as such by PIL, eg .webp
                return {'error': format_error_msg}
            except ValueError as e:
                return {'error': e.args[0]}

        self._clean_context()
        attachment = self._attachment_create(name=name, data=data, res_id=res_id, res_model=res_model)
        return attachment._get_media_info()

    @http.route(['/web_editor/attachment/add_url', '/html_editor/attachment/add_url'], type='jsonrpc', auth='user', methods=['POST'], website=True)
    def add_url(self, url, res_id=False, res_model='ir.ui.view', **kwargs):
        self._clean_context()
        attachment = self._attachment_create(url=url, res_id=res_id, res_model=res_model)
        return attachment._get_media_info()

    @http.route(['/web_editor/modify_image/<model("ir.attachment"):attachment>', '/html_editor/modify_image/<model("ir.attachment"):attachment>'], type="jsonrpc", auth="user", website=True)
    def modify_image(self, attachment, res_model=None, res_id=None, name=None, data=None, original_id=None, mimetype=None, alt_data=None):
        """
        Creates a modified copy of an attachment and returns its image_src to be
        inserted into the DOM.
        """
        self._clean_context()
        attachment = request.env['ir.attachment'].browse(attachment.id)
        fields = {
            'original_id': attachment.id,
            'datas': data,
            'type': 'binary',
            'res_model': res_model or 'ir.ui.view',
            'mimetype': mimetype or attachment.mimetype,
            'name': name or attachment.name,
        }
        if fields['res_model'] == 'ir.ui.view':
            fields['res_id'] = 0
        elif res_id:
            fields['res_id'] = res_id
        if fields['mimetype'] == 'image/webp':
            fields['name'] = re.sub(r'\.(jpe?g|png)$', '.webp', fields['name'], flags=re.I)
        existing_attachment = get_existing_attachment(request.env['ir.attachment'], fields)
        if existing_attachment and not existing_attachment.url:
            attachment = existing_attachment
        else:
            attachment = attachment.copy(fields)
        if alt_data:
            for size, per_type in alt_data.items():
                reference_id = attachment.id
                if 'image/webp' in per_type:
                    resized = attachment.create_unique([{
                        'name': attachment.name,
                        'description': 'resize: %s' % size,
                        'datas': per_type['image/webp'],
                        'res_id': reference_id,
                        'res_model': 'ir.attachment',
                        'mimetype': 'image/webp',
                    }])
                    reference_id = resized[0]
                if 'image/jpeg' in per_type:
                    attachment.create_unique([{
                        'name': re.sub(r'\.webp$', '.jpg', attachment.name, flags=re.I),
                        'description': 'format: jpeg',
                        'datas': per_type['image/jpeg'],
                        'res_id': reference_id,
                        'res_model': 'ir.attachment',
                        'mimetype': 'image/jpeg',
                    }])
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

    @http.route(['/web_editor/save_library_media', '/html_editor/save_library_media'], type='jsonrpc', auth='user', methods=['POST'])
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

        slug = request.env['ir.http']._slug
        for id, url in response.json().items():
            req = requests.get(url)
            name = '_'.join([media[id]['query'], url.split('/')[-1]])
            IrAttachment = request.env['ir.attachment']
            attachment_data = {
                'name': name,
                'mimetype': req.headers['content-type'],
                'public': True,
                'raw': req.content,
                'res_model': 'ir.ui.view',
                'res_id': 0,
            }
            attachment = get_existing_attachment(IrAttachment, attachment_data)
            # Need to bypass security check to write image with mimetype image/svg+xml
            # ok because svgs come from whitelisted origin
            if not attachment:
                attachment = IrAttachment.with_user(SUPERUSER_ID).create(attachment_data)
            if media[id]['is_dynamic_svg']:
                colorParams = werkzeug.urls.url_encode(media[id]['dynamic_colors'])
                attachment['url'] = '/html_editor/shape/illustration/%s?%s' % (slug(attachment), colorParams)
            attachments.append(attachment._get_media_info())

        return attachments

    @http.route(['/web_editor/shape/<module>/<path:filename>', '/html_editor/shape/<module>/<path:filename>'], type='http', auth="public", website=True)
    def shape(self, module, filename, **kwargs):
        """
        Returns a color-customized svg (background shape or illustration).
        """
        svg = None
        if module == 'illustration':
            unslug = request.env['ir.http']._unslug
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
            svg = svg.replace('<svg ', '<svg style="transform: scaleX(-1);" ', 1)
        elif flip_value == 'y':
            svg = svg.replace('<svg ', '<svg style="transform: scaleY(-1)" ', 1)
        elif flip_value == 'xy':
            svg = svg.replace('<svg ', '<svg style="transform: scale(-1)" ', 1)

        shape_animation_speed = float(options.get('shapeAnimationSpeed', 0.0))
        if shape_animation_speed != 0.0:
            svg = self.replace_animation_duration(
                shape_animation_speed=shape_animation_speed,
                svg=svg
            )
        return request.make_response(svg, [
            ('Content-type', 'image/svg+xml'),
            ('Cache-control', 'max-age=%s' % http.STATIC_CACHE_LONG),
        ])

    @http.route(["/web_editor/generate_text", "/html_editor/generate_text"], type="jsonrpc", auth="user")
    def generate_text(self, prompt, conversation_history):
        try:
            IrConfigParameter = request.env['ir.config_parameter'].sudo()
            olg_api_endpoint = IrConfigParameter.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            database_id = IrConfigParameter.get_param('database.uuid')
            response = iap_tools.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': prompt,
                'conversation_history': conversation_history or [],
                'database_id': database_id,
            }, timeout=30)
            if response['status'] == 'success':
                return response['content']
            elif response['status'] == 'error_prompt_too_long':
                raise UserError(_("Sorry, your prompt is too long. Try to say it in fewer words."))
            elif response['status'] == 'limit_call_reached':
                raise UserError(_("You have reached the maximum number of requests for this service. Try again later."))
            else:
                raise UserError(_("Sorry, we could not generate a response. Please try again later."))
        except AccessError:
            raise AccessError(_("Oops, it looks like our AI is unreachable!"))

    @http.route(["/web_editor/get_ice_servers", "/html_editor/get_ice_servers"], type='jsonrpc', auth="user")
    def get_ice_servers(self):
        return request.env['mail.ice.server']._get_ice_servers()

    @http.route(["/web_editor/bus_broadcast", "/html_editor/bus_broadcast"], type="jsonrpc", auth="user")
    def bus_broadcast(self, model_name, field_name, res_id, bus_data):
        document = request.env[model_name].browse([res_id])

        document.check_access('read')
        document.check_access('write')
        if field := document._fields.get(field_name):
            document._check_field_access(field, 'read')
            document._check_field_access(field, 'write')

        channel = (request.db, 'editor_collaboration', model_name, field_name, int(res_id))
        bus_data.update({'model_name': model_name, 'field_name': field_name, 'res_id': res_id})
        request.env['bus.bus']._sendone(channel, 'editor_collaboration', bus_data)

    @http.route('/html_editor/link_preview_external', type="jsonrpc", auth="public", methods=['POST'])
    def link_preview_metadata(self, preview_url):
        return link_preview.get_link_preview_from_url(preview_url)

    @http.route('/html_editor/link_preview_internal', type="jsonrpc", auth="user", methods=['POST'])
    def link_preview_metadata_internal(self, preview_url):
        try:
            Actions = request.env['ir.actions.actions']
            context = dict(request.env.context)
            words = preview_url.strip('/').split('/')

            record_id = int(words.pop())
            action_name = words.pop()
            if (action_name.startswith('m-') or '.' in action_name) and action_name in request.env and not request.env[action_name]._abstract:
                # if path format is `odoo/<model>/<record_id>` so we use `action_name` as model name
                model_name = action_name.removeprefix('m-')
                model = request.env[model_name].with_context(context)
            else:
                action = Actions.sudo().search([('path', '=', action_name)])
                if not action:
                    return {'error_msg': _("Action %s not found, link preview is not available, please check your url is correct", action_name)}
                action_type = action.type
                if action_type != 'ir.actions.act_window':
                    return {'other_error_msg': _("Action %s is not a window action, link preview is not available", action_name)}
                action = request.env[action_type].browse(action.id)

                model = request.env[action.res_model].with_context(context)
                
            record = model.browse(record_id)

            result = {}
            if 'description' in record:
                result['description'] = record.description

            if 'link_preview_name' in record:
                result['link_preview_name'] = record.link_preview_name
            elif 'display_name' in record:
                result['display_name'] = record.display_name

            return result
        except (MissingError) as e:
            return {'error_msg': _("Link preview is not available because %s, please check if your url is correct", str(e))}
        # catch all other exceptions and return the error message to display in the console but not blocking the flow
        except Exception as e:  # noqa: BLE001
            return {'other_error_msg': str(e)}
