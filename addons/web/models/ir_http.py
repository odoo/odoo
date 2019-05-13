# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import json
import logging
import unicodedata

from odoo import api, models, _
from odoo.http import request
from odoo.tools import ustr

from odoo.addons.web.controllers.main import concat_xml, manifest_glob, module_boot

import odoo

_logger = logging.getLogger(__name__)


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

        user_context = request.session.get_context() if request.session.uid else {}

        mods = module_boot()
        files = [f[0] for f in manifest_glob('qweb', addons=','.join(mods))]
        _, qweb_checksum = concat_xml(files)

        lang = user_context.get("lang")
        translations_per_module, _ = request.env['ir.translation'].get_translations_for_webclient(mods, lang)

        menu_json_utf8 = json.dumps(request.env['ir.ui.menu'].load_menus(request.session.debug), default=ustr, sort_keys=True).encode()
        translations_json_utf8 = json.dumps(translations_per_module,  sort_keys=True).encode()

        return {
            "uid": request.session.uid,
            "is_system": user._is_system() if request.session.uid else False,
            "is_admin": user._is_admin() if request.session.uid else False,
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "name": user.name,
            "username": user.login,
            "partner_display_name": user.partner_id.display_name,
            "company_id": user.company_id.id if request.session.uid else None,  # YTI TODO: Remove this from the user context
            "partner_id": user.partner_id.id if request.session.uid and user.partner_id else None,
            # current_company should be default_company
            "user_companies": {'current_company': (user.company_id.id, user.company_id.name), 'allowed_companies': [(comp.id, comp.name) for comp in user.company_ids]},
            "currencies": self.get_currencies() if request.session.uid else {},
            "web.base.url": self.env['ir.config_parameter'].sudo().get_param('web.base.url', default=''),
            "show_effect": True,
            "display_switch_company_menu": user.has_group('base.group_multi_company') and len(user.company_ids) > 1,
            "cache_hashes": {
                "load_menus": hashlib.sha1(menu_json_utf8).hexdigest(),
                "qweb": qweb_checksum,
                "translations": hashlib.sha1(translations_json_utf8).hexdigest(),
            },
        }

    @api.model
    def get_frontend_session_info(self):
        return {
            'is_admin': self.env.user._is_admin(),
            'is_system': self.env.user._is_system(),
            'is_website_user': self.env.user._is_public(),
            'user_id': self.env.user.id,
            'is_frontend': True,
        }

    def get_currencies(self):
        Currency = request.env['res.currency']
        currencies = Currency.search([]).read(['symbol', 'position', 'decimal_places'])
        return {c['id']: {'symbol': c['symbol'], 'position': c['position'], 'digits': [69,c['decimal_places']]} for c in currencies}

    def _neuter_mimetype(self, mimetype, user):
        wrong_type = 'ht' in mimetype or 'xml' in mimetype or 'svg' in mimetype
        if wrong_type and not user._is_system():
            return 'text/plain'
        return mimetype

    def _process_uploaded_files(self, files, model, res_id, generate_token=False):
        Model = self.env['ir.attachment']
        args = []
        for ufile in files:

            filename = ufile.filename
            mimetype = self._neuter_mimetype(ufile.content_type, request.env.user)
            if request.httprequest.user_agent.browser == 'safari':
                # Safari sends NFD UTF-8 (where é is composed by 'e' and [accent])
                # we need to send it the same stuff, otherwise it'll fail
                filename = unicodedata.normalize('NFD', ufile.filename)
            try:
                attachment = Model.create({
                    'name': filename,
                    'mimetype': mimetype,
                    'datas': base64.encodebytes(ufile.read()),
                    'res_model': model,
                    'res_id': int(res_id)
                })
                if generate_token:
                    attachment.generate_access_token()
                attachment._post_add_create()
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s" % ufile.filename)
            else:
                args.append({
                    'filename': filename,
                    'mimetype': mimetype,
                    'id': attachment.id,
                    'size': attachment.file_size,
                    'access_token': attachment.access_token,
                })
        return args
