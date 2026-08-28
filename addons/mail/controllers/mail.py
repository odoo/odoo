import io
import logging
from math import floor
from urllib.parse import parse_qsl, urlencode, urlparse

from PIL import Image, ImageColor, ImageDraw, ImageFont
from werkzeug.exceptions import NotFound
from werkzeug.urls import url_encode

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import Response, request
from odoo.http.stream import STATIC_CACHE
from odoo.tools import consteq
from odoo.tools.misc import file_open

from odoo.addons.mail.tools.discuss import add_guest_to_context
from odoo.addons.html_editor.controllers.ms_icons import MS_ICONS

try:
    from werkzeug.utils import send_file
except ImportError:
    from .tools._vendor.send_file import send_file

_logger = logging.getLogger(__name__)


class MailController(http.Controller):
    _cp_path = '/mail'

    @classmethod
    def _redirect_to_generic_fallback(cls, model, res_id, access_token=None, **kwargs):
        if request.session.uid is None:
            return cls._redirect_to_login_with_mail_view(
                model, res_id, access_token=access_token, **kwargs,
            )
        return cls._redirect_to_messaging()

    @classmethod
    def _redirect_to_messaging(cls):
        url = '/odoo/action-mail.action_discuss'
        return request.redirect(url)

    @classmethod
    def _redirect_to_login_with_mail_view(cls, model, res_id, access_token=None, **kwargs):
        url_base = '/mail/view'
        url_params = request.env['mail.thread']._get_action_link_params(
            'view', model=model, res_id=res_id, access_token=access_token, **kwargs,
        )
        mail_view_url = f'{url_base}?{url_encode(url_params, sort=True)}'
        return request.redirect(f'/web/login?{url_encode({"redirect": mail_view_url})}')

    @classmethod
    def _check_token(cls, token):
        base_link = request.httprequest.path
        params = dict(request.params)
        params.pop('token', '')
        valid_token = request.env['mail.thread']._encode_link(base_link, params)
        return consteq(valid_token, str(token))

    @classmethod
    def _check_token_and_record_or_redirect(cls, model, res_id, token):
        comparison = cls._check_token(token)
        if not comparison:
            _logger.warning('Invalid token in route %s', request.httprequest.url)
            return comparison, None, cls._redirect_to_generic_fallback(model, res_id)
        try:
            record = request.env[model].browse(res_id).exists()
        except Exception:
            record = None
            redirect = cls._redirect_to_generic_fallback(model, res_id)
        else:
            redirect = cls._redirect_to_record(model, res_id)
        return comparison, record, redirect

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        # access_token and kwargs are used in the portal controller override for the Send by email or Share Link
        # to give access to the record to a recipient that has normally no access.
        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        cids = []

        # no model / res_id, meaning no possible record -> redirect to login
        if not model or not res_id or model not in request.env:
            return cls._redirect_to_generic_fallback(
                model, res_id, access_token=access_token, **kwargs,
            )

        # find the access action using sudo to have the details about the access link
        RecordModel = request.env[model]
        record_sudo = RecordModel.sudo().browse(res_id).exists()
        if not record_sudo:
            # record does not seem to exist -> redirect to login
            return cls._redirect_to_generic_fallback(
                model, res_id, access_token=access_token, **kwargs,
            )

        suggested_company = record_sudo._get_redirect_suggested_company()
        # the record has a window redirection: check access rights
        if uid is not None:
            if not RecordModel.with_user(uid).has_access('read'):
                return cls._redirect_to_generic_fallback(
                    model, res_id, access_token=access_token, **kwargs,
                )
            try:
                # We need here to extend the "allowed_company_ids" to allow a redirection
                # to any record that the user can access, regardless of currently visible
                # records based on the "currently allowed companies".
                cids_str = request.cookies.get('cids', str(user.company_id.id))
                cids = [int(cid) for cid in cids_str.split('-')]
                try:
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids).check_access('read')
                except AccessError:
                    # In case the allowed_company_ids from the cookies (i.e. the last user configuration
                    # on their browser) is not sufficient to avoid an ir.rule access error, try to following
                    # heuristic:
                    # - Guess the supposed necessary company to access the record via the method
                    #   _get_redirect_suggested_company
                    #   - If no company, then redirect to the messaging
                    #   - Merge the suggested company with the companies on the cookie
                    # - Make a new access test if it succeeds, redirect to the record. Otherwise,
                    #   redirect to the messaging.
                    if not suggested_company:
                        raise AccessError(_("There is no candidate company that has read access to the record."))
                    cids = cids + [suggested_company.id]
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids).check_access('read')
                    request.future_response.set_cookie('cids', '-'.join([str(cid) for cid in cids]))
            except AccessError:
                return cls._redirect_to_generic_fallback(
                    model, res_id, access_token=access_token, **kwargs,
                )
            else:
                record_action = record_sudo._get_access_action(access_uid=uid)
        else:
            record_action = record_sudo._get_access_action()
            # we have an act_url (probably a portal link): we need to retry being logged to check access
            if record_action['type'] == 'ir.actions.act_url' and record_action.get('target_type') != 'public':
                return cls._redirect_to_login_with_mail_view(
                    model, res_id, access_token=access_token, **kwargs,
                )

        record_action.pop('target_type', None)
        # the record has an URL redirection: use it directly
        if record_action['type'] == 'ir.actions.act_url':
            url = record_action["url"]
            if highlight_message_id := kwargs.get("highlight_message_id"):
                parsed_url = urlparse(url)
                url = parsed_url._replace(query=urlencode(
                    parse_qsl(parsed_url.query) + [("highlight_message_id", highlight_message_id)]
                )).geturl()
            return request.redirect(url)
        # anything else than an act_window is not supported
        elif record_action['type'] != 'ir.actions.act_window':
            return cls._redirect_to_messaging()

        # backend act_window: when not logged, unless really readable as public,
        # user is going to be redirected to login -> keep mail/view as redirect
        # in that case. In case of readable record, we consider this might be
        # a customization and we do not change the behavior in stable
        if uid is None or request.env.user._is_public():
            has_access = record_sudo.with_user(request.env.user).has_access('read')
            if not has_access:
                return cls._redirect_to_login_with_mail_view(
                    model, res_id, access_token=access_token, **kwargs,
                )

        url_params = {}
        menu_id = request.env['ir.ui.menu']._get_best_backend_root_menu_id_for_model(model)
        if menu_id:
            url_params['menu_id'] = menu_id
        view_id = record_sudo.get_formview_id()
        if view_id:
            url_params['view_id'] = view_id
        if highlight_message_id := kwargs.get("highlight_message_id"):
            url_params["highlight_message_id"] = highlight_message_id
        if cids:
            request.future_response.set_cookie('cids', '-'.join([str(cid) for cid in cids]))

        # @see commit c63d14a0485a553b74a8457aee158384e9ae6d3f
        # @see router.js: heuristics to discrimate a model name from an action path
        # is the presence of dots, or the prefix m- for models
        model_in_url = model if "." in model else "m-" + model
        url = f'/odoo/{model_in_url}/{res_id}?{url_encode(url_params, sort=True)}'
        return request.redirect(url)

    @staticmethod
    def _get_icon_rendering_info(icon, font, fill=False):
        info = {}
        if font == 'oi' and icon.isdigit():
            # custom odoo icon
            info['path'] = 'web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff2'
            info['icon'] = chr(int(icon))
        elif font == 'fa':
            # legacy fontawesome icon
            info['path'] = 'web/static/src/libs/fontawesome/fonts/fontawesome-webfont.ttf'
            info['icon'] = chr(int(icon)) if icon.isdigit() else icon  # legacy fallback
        else:
            # default to 'oi' (material icons)
            info['path'] = 'web/static/src/libs/materialsymbols/material_symbols_backend.woff'
            codepoint = MS_ICONS[icon]['codepoint']
            if fill:
                codepoint = 0x100000 + (codepoint & 0xFFFF)
            info['icon'] = chr(codepoint)
        return info

    @http.route('/mail/view', type='http', auth='public')
    def mail_action_view(self, model=None, res_id=None, access_token=None, **kwargs):
        """ Generic access point from notification emails. The heuristic to
            choose where to redirect the user is the following :

         - find a public URL
         - if none found

          - users with a read access are redirected to the document
          - users without read access are redirected to the Messaging
          - not logged users are redirected to the login page

            models that have an access_token may apply variations on this.
        """
        # ==============================================================================================
        # This block of code disappeared on saas-11.3 to be reintroduced by TBE.
        # This is needed because after a migration from an older version to saas-11.3, the link
        # received by mail with a message_id no longer work.
        # So this block of code is needed to guarantee the backward compatibility of those links.
        if kwargs.get('message_id'):
            try:
                message = request.env['mail.message'].sudo().browse(int(kwargs['message_id'])).exists()
            except:
                message = request.env['mail.message']
            if message:
                model, res_id = message.model, message.res_id
        # ==============================================================================================

        if res_id and isinstance(res_id, str):
            try:
                res_id = int(res_id)
            except ValueError:
                res_id = False
        return self._redirect_to_record(model, res_id, access_token, **kwargs)

    # csrf is disabled here because it will be called by the MUA with unpredictable session at that time
    @http.route('/mail/unfollow', type='http', auth='public', csrf=False)
    def mail_action_unfollow(self, model, res_id, pid, token, **kwargs):
        comparison, record, __ = MailController._check_token_and_record_or_redirect(model, int(res_id), token)
        if not comparison or not record:
            raise AccessError(_('Non existing record or wrong token.'))

        pid = int(pid)
        record_sudo = record.sudo()
        record_sudo.message_unsubscribe([pid])

        display_link = True
        if request.session.uid:
            display_link = record.has_access('read')

        return request.render('mail.message_document_unfollowed', {
            'name': record_sudo.display_name,
            'model_name': request.env['ir.model'].sudo()._get(model).display_name,
            'access_url': record_sudo._notify_get_action_link('view') if display_link else False,
        })

    @http.route('/mail/message/<int:message_id>', type='http', auth='public')
    @add_guest_to_context
    def mail_thread_message_redirect(self, message_id, **kwargs):
        message = request.env['mail.message'].search([('id', '=', message_id)])
        if not message:
            if request.env.user._is_public():
                return request.redirect(f'/web/login?redirect=/mail/message/{message_id}')
            raise NotFound()

        return self._redirect_to_record(message.model, message.res_id, highlight_message_id=message_id)

    # web_editor routes need to be kept otherwise mail already sent won't be able to load icons anymore
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
        '/mail/font_to_img/<icon>',
        '/mail/font_to_img/<icon>/<color>',
        '/mail/font_to_img/<icon>/<color>/<int:size>',
        '/mail/font_to_img/<icon>/<color>/<int:width>x<int:height>',
        '/mail/font_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        '/mail/font_to_img/<icon>/<color>/<int:width>x<int:height>/<int:alpha>',
        '/mail/font_to_img/<icon>/<color>/<bg>',
        '/mail/font_to_img/<icon>/<color>/<bg>/<int:size>',
        '/mail/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>',
        '/mail/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>/<int:alpha>',
        ], type='http', auth='none')
    def export_icon_to_png_legacy(self, icon, color='#000', bg=None, size=100, alpha=255, font='fa', width=None, height=None):
        """ This legacy method converts an unicode character to an image (using Font
            Awesome font by default) and is used only for mass mailing because
            custom fonts are not supported in mail.
            :param icon : string or decimal encoding of unicode character
            :param color : RGB code of the color
            :param bg : RGB code of the background color
            :param size : Pixels in integer
            :param alpha : (unused) transparency of the image from 0 to 255
            :param font : font key ('fa' or 'oi')
            :param width : Pixels in integer
            :param height : Pixels in integer

            :returns PNG image converted from given font
        """
        # --- Legacy font and icon normalization
        # For custom icons, use the corresponding custom font
        if icon.isdigit():
            oi_font_char_codes = {
                # Replacement of existing Twitter icons by X icons (the route
                # here receives the old icon code always, but the replacement
                # one is also considered for consistency anyway).
                '61569': '59464',  # F081 -> E848: oi_x-square
                '61593': '59418',  # F099 -> E81A: oi_x

                # Addition of new icons
                '59407': '59407',  # E80F: oi_strava
                '59409': '59409',  # E811: oi_discord
                '59416': '59416',  # E818: oi_threads
                '59417': '59417',  # E819: oi_kickstarter
                '59418': '59418',  # E81A: oi_twitter
                '59419': '59419',  # E81B: oi_tiktok
                '59420': '59420',  # E81C: oi_bluesky
                '59421': '59421',  # E81D: oi_google-play
                '59464': '59464',  # E848: oi_twitter-square
            }
            if icon in oi_font_char_codes:
                icon = oi_font_char_codes[icon]
                font = 'oi'

        # --- Legacy bg and color normalization
        def normalize_color(hex_color, default):
            try:
                # Convert the opacity value compatible with PIL Image color
                # (0 to 255) when color specifier is 'rgba'
                if hex_color.startswith('rgba'):
                    *rgb, a = hex_color.strip(')').split(',')
                    opacity = str(floor(float(a) * 255))
                    hex_color = ','.join([*rgb, opacity]) + ')'
                return ''.join(f'{n:02x}' for n in ImageColor.getrgb(hex_color))
            except ValueError:
                return default
        bg = normalize_color(bg, '00000000') if bg else '00000000'
        color = normalize_color(color, '000000ff')

        # --- Legacy height, width and font_size normalization
        size = max(width, height, 1) if width else size
        width = width or size
        height = height or size
        # Make sure we have at least size=1
        width = max(1, min(width, 512))
        height = max(1, min(height, 512))
        font_size = height

        return self.export_icon_to_png(icon, font=font, fill=0, color=color, bg=bg, width=width, height=height, font_size=font_size)

    # all routes need to be kept otherwise mail already sent won't be able to load icons anymore
    @http.route([
        '/mail/font_to_img/<icon>/<font>/<int:fill>/<color>/<bg>/<int:width>x<int:height>fs<int:font_size>',
    ], type='http', auth='none')
    def export_icon_to_png(self, icon, font='oi', fill=0, color='000000ff', bg='00000000', width=16, height=16, font_size=16):
        """ Convert an icon to an image. Is used only for mass mailing because
            custom fonts are not supported in mail.
            :param icon : icon ligature, or decimal encoding of unicode
              character
            :param font : font key ('fa' or 'oi')
            :param fill : FILL axis (0 or 1), ignored if not relevant
            :param color : font color RGB or RGBA hexadecimal string
            :param bg : background color RGB or RGBA hexadecimal string
            :param width : Pixels in integer
            :param height : Pixels in integer
            :param font_size : Pixels in integer

            :returns PNG image converted from given font
        """
        rendering_info = self._get_icon_rendering_info(icon, font, bool(fill))
        font_path = rendering_info['path']
        layout_engine = rendering_info.get('layout_engine')
        features = rendering_info.get('features')
        icon = rendering_info['icon']

        # Format colors for PIL
        color = '#' + str.lower(color)
        color_tuple = ImageColor.getrgb(color)
        alpha = color_tuple[3] if len(color_tuple) == 4 else 255
        bg = '#' + str.lower(bg)
        # Make sure size >= 1, keep requested aspect ratio and
        # clamp maximum output dimension to 512
        width = max(1, width)
        height = max(1, height)
        font_size = max(1, font_size)
        max_size = max(width, height, font_size)
        if max_size > 512:
            scale = 512 / max_size
            width = max(1, round(width * scale))
            height = max(1, round(height * scale))
            font_size = max(1, round(font_size * scale))
        # Determine the dimensions of the icon using a dummy draw
        draw = ImageDraw.Draw(Image.new('L', (1, 1)))
        fd = None

        def extract_font_info():
            fd = file_open(font_path, 'rb')
            font_obj = ImageFont.truetype(fd, font_size, layout_engine=layout_engine)
            box = draw.textbbox((0, 0), icon, font=font_obj, features=features)
            box_w = box[2] - box[0]
            box_h = box[3] - box[1]
            return fd, font_obj, box, box_w, box_h
        try:
            fd, font_obj, box, box_w, box_h = extract_font_info()
            max_ratio = max(box_w / width, box_h / height)
            if max_ratio > 1:
                # the old font_obj will no longer be used
                fd.close()
                fd = None
                # adjust the font_size to fit in requested dimensions
                font_size = max(1, int(font_size / max_ratio))
                fd, font_obj, box, box_w, box_h = extract_font_info()
            left, top = box[:2]

            # Create an alpha mask
            image_mask = Image.new('L', (box_w, box_h), 0)
            draw_mask = ImageDraw.Draw(image_mask)
            draw_mask.text((-left, -top), icon, font=font_obj, features=features, fill=255)
            ink_box = image_mask.getbbox()
            if ink_box is not None:
                image_mask = image_mask.crop(ink_box)
            box_w, box_h = image_mask.size
            image_mask = image_mask.point(lambda p: p * alpha // 255)

            # Create a colored rectangle and apply the alpha mask
            icon_image = Image.new('RGBA', (box_w, box_h), color_tuple[:3])
            icon_image.putalpha(image_mask)

            out_w = max(width, box_w)
            out_h = max(height, box_h)
            x = round((out_w - box_w) / 2)
            y = round((out_h - box_h) / 2)

            # Create output image
            out_image = Image.new('RGBA', (out_w, out_h), bg)
            out_image.alpha_composite(icon_image, dest=(x, y))
            output = io.BytesIO()
            out_image.save(output, format='PNG')
            output.seek(0)
        finally:
            if fd is not None:
                fd.close()
        response = send_file(
            output,
            request.httprequest.environ,
            mimetype='image/png',
            conditional=False,
            etag=False,
            max_age=STATIC_CACHE,
            response_class=Response,
        )
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        return response
