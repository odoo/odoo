# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import psycopg2
import werkzeug

from operator import itemgetter
from werkzeug import url_encode

from odoo import api, http, registry, SUPERUSER_ID, _
from odoo.addons.web.controllers.main import binary_content
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MailController(http.Controller):
    _cp_path = '/mail'

    @classmethod
    def _redirect_to_messaging(cls):
        messaging_action = request.env['mail.thread']._get_inbox_action_xml_id()
        url = '/web#%s' % url_encode({'action': messaging_action})
        return werkzeug.utils.redirect(url)

    @classmethod
    def _check_token(cls, token):
        base_link = request.httprequest.path
        params = dict(request.params)
        params.pop('token', '')
        valid_token = request.env['mail.thread']._generate_notification_token(base_link, params)
        return consteq(valid_token, str(token))

    @classmethod
    def _check_token_and_record_or_redirect(cls, model, res_id, token):
        comparison = cls._check_token(token)
        if not comparison:
            _logger.warning(_('Invalid token in route %s') % request.httprequest.url)
            return comparison, None, cls._redirect_to_messaging()
        try:
            record = request.env[model].browse(res_id).exists()
        except Exception:
            record = None
            redirect = cls._redirect_to_messaging()
        else:
            redirect = cls._redirect_to_record(model, res_id)
        return comparison, record, redirect

    @classmethod
    def _redirect_to_record(cls, model, res_id):
        uid = request.session.uid

        # no model / res_id, meaning no possible record -> redirect to login
        if not model or not res_id or model not in request.env:
            return cls._redirect_to_messaging()

        # find the access action using sudo to have the details about the access link
        RecordModel = request.env[model]
        record_sudo = RecordModel.sudo().browse(res_id).exists()
        if not record_sudo:
            # record does not seem to exist -> redirect to login
            return cls._redirect_to_messaging()
        record_action = record_sudo.get_access_action()

        # the record has an URL redirection: use it directly
        if record_action['type'] == 'ir.actions.act_url':
            return werkzeug.utils.redirect(record_action['url'])
        # other choice: act_window (no support of anything else currently)
        elif not record_action['type'] == 'ir.actions.act_window':
            return cls._redirect_to_messaging()

        # the record has a window redirection: check access rights
        if not RecordModel.sudo(uid).check_access_rights('read', raise_exception=False):
            return cls._redirect_to_messaging()
        try:
            record_sudo.sudo(uid).check_access_rule('read')
        except AccessError:
            return cls._redirect_to_messaging()

        url_params = {
            'view_type': record_action['view_type'],
            'model': model,
            'id': res_id,
            'active_id': res_id,
            'view_id': record_sudo.get_formview_id(),
            'action': record_action.get('id'),
        }
        url = '/web?#%s' % url_encode(url_params)
        return werkzeug.utils.redirect(url)

    @http.route('/mail/receive', type='json', auth='none')
    def receive(self, req):
        """ End-point to receive mail from an external SMTP server. """
        dbs = req.jsonrequest.get('databases')
        for db in dbs:
            message = dbs[db].decode('base64')
            try:
                db_registry = registry(db)
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    env['mail.thread'].message_process(None, message)
            except psycopg2.Error:
                pass
        return True

    @http.route('/mail/read_followers', type='json', auth='user')
    def read_followers(self, follower_ids, res_model):
        followers = []
        is_editable = request.env.user.has_group('base.group_no_one')
        partner_id = request.env.user.partner_id
        follower_id = None
        for follower in request.env['mail.followers'].browse(follower_ids):
            is_uid = partner_id == follower.partner_id
            follower_id = follower.id if is_uid else follower_id
            followers.append({
                'id': follower.id,
                'name': follower.partner_id.name or follower.channel_id.name,
                'email': follower.partner_id.email if follower.partner_id else None,
                'res_model': 'res.partner' if follower.partner_id else 'mail.channel',
                'res_id': follower.partner_id.id or follower.channel_id.id,
                'is_editable': is_editable,
                'is_uid': is_uid,
            })
        return {
            'followers': followers,
            'subtypes': self.read_subscription_data(res_model, follower_id) if follower_id else None
        }

    @http.route('/mail/read_subscription_data', type='json', auth='user')
    def read_subscription_data(self, res_model, follower_id):
        """ Computes:
            - message_subtype_data: data about document subtypes: which are
                available, which are followed if any """
        followers = request.env['mail.followers'].browse(follower_id)

        # find current model subtypes, add them to a dictionary
        subtypes = request.env['mail.message.subtype'].search(['&', ('hidden', '=', False), '|', ('res_model', '=', res_model), ('res_model', '=', False)])
        subtypes_list = [{
            'name': subtype.name,
            'res_model': subtype.res_model,
            'sequence': subtype.sequence,
            'default': subtype.default,
            'internal': subtype.internal,
            'followed': subtype.id in followers.mapped('subtype_ids').ids,
            'parent_model': subtype.parent_id and subtype.parent_id.res_model or False,
            'id': subtype.id
        } for subtype in subtypes]
        subtypes_list = sorted(subtypes_list, key=itemgetter('parent_model', 'res_model', 'internal', 'sequence'))
        return subtypes_list

    @http.route('/mail/view', type='http', auth='none')
    def mail_action_view(self, model=None, res_id=None, message_id=None):
        """ Generic access point from notification emails. The heuristic to
        choose where to redirect the user is the following :

         - find a public URL
         - if none found
          - users with a read access are redirected to the document
          - users without read access are redirected to the Messaging
          - not logged users are redirected to the login page
        """
        if message_id:
            try:
                message = request.env['mail.message'].sudo().browse(int(message_id)).exists()
            except:
                message = request.env['mail.message']
            if message:
                model, res_id = message.model, message.res_id
            else:
                # either a wrong message_id, either someone trying ids -> just go to messaging
                return self._redirect_to_messaging()
        elif res_id and isinstance(res_id, basestring):
            res_id = int(res_id)

        return self._redirect_to_record(model, res_id)

    @http.route('/mail/follow', type='http', auth='user', methods=['GET'])
    def mail_action_follow(self,  model, res_id, token=None):
        comparison, record, redirect = self._check_token_and_record_or_redirect(model, int(res_id), token)
        if comparison and record:
            try:
                record.sudo().message_subscribe_users()
            except Exception:
                return self._redirect_to_messaging()
        return redirect

    @http.route('/mail/unfollow', type='http', auth='user', methods=['GET'])
    def mail_action_unfollow(self, model, res_id, token=None):
        comparison, record, redirect = self._check_token_and_record_or_redirect(model, int(res_id), token)
        if comparison and record:
            try:
                # TDE CHECKME: is sudo really necessary ?
                record.sudo().message_unsubscribe_users([request.uid])
            except Exception:
                return self._redirect_to_messaging()
        return redirect

    @http.route('/mail/new', type='http', auth='user')
    def mail_action_new(self, model, res_id, action_id):
        if model not in request.env:
            return self._redirect_to_messaging()
        params = {'view_type': 'form', 'model': model}
        if action_id:
            # Probably something to do
            params['action'] = action_id
        return werkzeug.utils.redirect('/web?#%s' % url_encode(params))

    @http.route('/mail/assign', type='http', auth='user', methods=['GET'])
    def mail_action_assign(self, model, res_id, token=None):
        comparison, record, redirect = self._check_token_and_record_or_redirect(model, int(res_id), token)
        if comparison and record:
            try:
                record.write({'user_id': request.uid})
            except Exception:
                return self._redirect_to_messaging()
        return redirect

    @http.route('/mail/<string:res_model>/<int:res_id>/avatar/<int:partner_id>', type='http', auth='public')
    def avatar(self, res_model, res_id, partner_id):
        headers = [('Content-Type', 'image/png')]
        status = 200
        content = 'R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='  # default image is one white pixel
        if res_model in request.env:
            try:
                # if the current user has access to the document, get the partner avatar as sudo()
                request.env[res_model].browse(res_id).check_access_rule('read')
                if partner_id in request.env[res_model].browse(res_id).sudo().exists().message_ids.mapped('author_id').ids:
                    status, headers, _content = binary_content(model='res.partner', id=partner_id, field='image_medium', default_mimetype='image/png', env=request.env(user=SUPERUSER_ID))
                    # binary content return an empty string and not a placeholder if obj[field] is False
                    if _content != '':
                        content = _content
                    if status == 304:
                        return werkzeug.wrappers.Response(status=304)
            except AccessError:
                pass
        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status = str(status)
        return response

    @http.route('/mail/needaction', type='json', auth='user')
    def needaction(self):
        return request.env['res.partner'].get_needaction_count()

    @http.route('/mail/client_action', type='json', auth='user')
    def mail_client_action(self):
        values = {
            'needaction_inbox_counter': request.env['res.partner'].get_needaction_count(),
            'starred_counter': request.env['res.partner'].get_starred_count(),
            'channel_slots': request.env['mail.channel'].channel_fetch_slot(),
            'commands': request.env['mail.channel'].get_mention_commands(),
            'mention_partner_suggestions': request.env['res.partner'].get_static_mention_suggestions(),
            'shortcodes': request.env['mail.shortcode'].sudo().search_read([], ['shortcode_type', 'source', 'substitution', 'description']),
            'menu_id': request.env['ir.model.data'].xmlid_to_res_id('mail.mail_channel_menu_root_chat'),
        }
        return values
