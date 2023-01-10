# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import json

import odoo
from odoo import api, http, models
from odoo.http import request
from odoo.tools import file_open, image_process, ustr

from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def webclient_rendering_context(self):
        return {
            'menu_data': request.env['ir.ui.menu'].load_menus(request.session.debug),
            'session_info': self.session_info(),
        }

    def session_info(self):
        user = request.env.user
        version_info = odoo.service.common.exp_version()

        session_uid = request.session.uid
        user_context = request.session.get_context() if session_uid else {}
        IrConfigSudo = self.env['ir.config_parameter'].sudo()
        max_file_upload_size = int(IrConfigSudo.get_param(
            'web.max_file_upload_size',
            default=128 * 1024 * 1024,  # 128MiB
        ))
        mods = odoo.conf.server_wide_modules or []
        lang = user_context.get("lang")
        translation_hash = request.env['ir.translation'].sudo().get_web_translations_hash(mods, lang)
        session_info = {
            "uid": session_uid,
            "is_system": user._is_system() if session_uid else False,
            "is_admin": user._is_admin() if session_uid else False,
            "user_context": user_context,
            "db": request.session.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "support_url": "https://www.odoo.com/buy",
            "name": user.name,
            "username": user.login,
            "partner_display_name": user.partner_id.display_name,
            "company_id": user.company_id.id if session_uid else None,  # YTI TODO: Remove this from the user context
            "partner_id": user.partner_id.id if session_uid and user.partner_id else None,
            "web.base.url": IrConfigSudo.get_param('web.base.url', default=''),
            "active_ids_limit": int(IrConfigSudo.get_param('web.active_ids_limit', default='20000')),
            'profile_session': request.session.profile_session,
            'profile_collectors': request.session.profile_collectors,
            'profile_params': request.session.profile_params,
            "max_file_upload_size": max_file_upload_size,
            "home_action_id": user.action_id.id,
            "cache_hashes": {
                "translations": translation_hash,
            },
            "currencies": self.sudo().get_currencies(),
        }
        if self.env.user.has_group('base.group_user'):
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            if request.db:
                mods = list(request.registry._init_modules) + mods
            qweb_checksum = HomeStaticTemplateHelpers.get_qweb_templates_checksum(debug=request.session.debug, bundle="web.assets_qweb")
            menus = request.env['ir.ui.menu'].load_menus(request.session.debug)
            ordered_menus = {str(k): v for k, v in menus.items()}
            menu_json_utf8 = json.dumps(ordered_menus, default=ustr, sort_keys=True).encode()
            session_info['cache_hashes'].update({
                "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[:64], # sha512/256
                "qweb": qweb_checksum,
            })
            session_info.update({
                # current_company should be default_company
                "user_companies": {
                    'current_company': user.company_id.id,
                    'allowed_companies': {
                        comp.id: {
                            'id': comp.id,
                            'name': comp.name,
                            'sequence': comp.sequence,
                        } for comp in user.company_ids
                    },
                },
                "show_effect": True,
                "display_switch_company_menu": user.has_group('base.group_multi_company') and len(user.company_ids) > 1,
            })
        return session_info

    @api.model
    def get_frontend_session_info(self):
        session_info = {
            'is_admin': request.session.uid and self.env.user._is_admin() or False,
            'is_system': request.session.uid and self.env.user._is_system() or False,
            'is_website_user': request.session.uid and self.env.user._is_public() or False,
            'user_id': request.session.uid and self.env.user.id or False,
            'is_frontend': True,
            'profile_session': request.session.profile_session,
            'profile_collectors': request.session.profile_collectors,
            'profile_params': request.session.profile_params,
            'show_effect': request.env['ir.config_parameter'].sudo().get_param('base_setup.show_effect'),
        }
        if request.session.uid:
            version_info = odoo.service.common.exp_version()
            session_info.update({
                'server_version': version_info.get('server_version'),
                'server_version_info': version_info.get('server_version_info')
            })
        return session_info

    def get_currencies(self):
        Currency = request.env['res.currency']
        currencies = Currency.search([]).read(['symbol', 'position', 'decimal_places'])
        return {c['id']: {'symbol': c['symbol'], 'position': c['position'], 'digits': [69,c['decimal_places']]} for c in currencies}

    @api.model
    def _get_content_common(self, xmlid=None, model='ir.attachment', res_id=None, field='datas',
            unique=None, filename=None, filename_field='name', download=None, mimetype=None,
            access_token=None, token=None):
        status, headers, content = self.binary_content(
            xmlid=xmlid, model=model, id=res_id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype, access_token=access_token
        )
        if status != 200:
            return self._response_by_status(status, headers, content)
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
        return response

    @api.model
    def _content_image(self, xmlid=None, model='ir.attachment', res_id=None, field='datas',
            filename_field='name', unique=None, filename=None, mimetype=None, download=None,
            width=0, height=0, crop=False, quality=0, access_token=None, **kwargs):
        status, headers, image_base64 = self.binary_content(
            xmlid=xmlid, model=model, id=res_id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype='image/png', access_token=access_token
        )
        return self._content_image_get_response(
            status, headers, image_base64, model=model, field=field, download=download,
            width=width, height=height, crop=crop, quality=quality)

    @api.model
    def _content_image_get_response(self, status, headers, image_base64, model='ir.attachment',
            field='datas', download=None, width=0, height=0, crop=False, quality=0):
        if status in [301, 304] or (status != 200 and download):
            return self._response_by_status(status, headers, image_base64)
        if not image_base64:
            placeholder_filename = False
            if model in self.env:
                placeholder_filename = self.env[model]._get_placeholder_filename(field)
            placeholder_content = self._placeholder(image=placeholder_filename)
            # Since we set a placeholder for any missing image, the status must be 200. In case one
            # wants to configure a specific 404 page (e.g. though nginx), a 404 status will cause
            # troubles.
            status = 200
            image_base64 = base64.b64encode(placeholder_content)
            if not (width or height):
                width, height = odoo.tools.image_guess_size_from_field_name(field)
        try:
            image_base64 = image_process(image_base64, size=(int(width), int(height)), crop=crop, quality=int(quality))
        except Exception:
            return request.not_found()
        content = base64.b64decode(image_base64)
        headers = http.set_safe_image_headers(headers, content)
        response = request.make_response(content, headers)
        response.status_code = status
        return response

    @api.model
    def _placeholder_image_get_response(self, placeholder_base64):
        content = base64.b64decode(placeholder_base64)
        headers = http.set_safe_image_headers([], content)
        response = request.make_response(content, headers)
        response.status_code = 200
        return response

    @api.model
    def _placeholder(self, image=False):
        if not image:
            image = 'web/static/img/placeholder.png'
        with file_open(image, 'rb', filter_ext=('.png', '.jpg')) as fd:
            return fd.read()
