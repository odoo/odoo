import io
import logging
import time

from math import floor
from PIL import Image, ImageFont, ImageDraw
from werkzeug.urls import url_encode
from werkzeug.exceptions import NotFound
from urllib.parse import parse_qsl, urlencode, urlparse

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request, Response
from odoo.tools import consteq
from odoo.addons.mail.tools.discuss import add_guest_to_context
from odoo.tools.misc import file_open

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
            'view', **{
                'model': model,
                'res_id': res_id,
                'access_token': access_token,
                **kwargs,
            }
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
            'access_url': record._notify_get_action_link('view', model=model, res_id=res_id) if display_link else False,
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
            oi_font_char_codes = {
                # Replacement of existing Twitter icons by X icons (the route
                # here receives the old icon code always, but the replacement
                # one is also considered for consistency anyway).
                "61569": "59464",  # F081 -> E848: fa-twitter-square
                "61593": "59418",  # F099 -> E81A: fa-twitter

                # Addition of new icons
                "59407": "59407",  # E80F: fa-strava
                "59409": "59409",  # E811: fa-discord
                "59416": "59416",  # E818: fa-threads
                "59417": "59417",  # E819: fa-kickstarter
                "59419": "59419",  # E81B: fa-tiktok
                "59420": "59420",  # E81C: fa-bluesky
                "59421": "59421",  # E81D: fa-google-play
            }
            if icon in oi_font_char_codes:
                icon = oi_font_char_codes[icon]
                font = "/web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff"

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
            bg = ','.join(bg.split(',')[:-1]) + ')'

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
            color = ','.join(color.split(',')[:-1]) + ')'
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
        response.headers['Expires'] = time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(time.time() + 604800 * 60))

        return response
