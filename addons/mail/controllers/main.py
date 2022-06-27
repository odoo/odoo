# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import psycopg2
import werkzeug.utils
import werkzeug.wrappers

from werkzeug.urls import url_encode

from odoo import api, http, registry, SUPERUSER_ID, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MailController(http.Controller):
    _cp_path = '/mail'

    @classmethod
    def _redirect_to_messaging(cls):
        url = '/web#%s' % url_encode({'action': 'mail.action_discuss'})
        return werkzeug.utils.redirect(url)

    @classmethod
    def _check_token(cls, token):
        base_link = request.httprequest.path
        params = dict(request.params)
        params.pop('token', '')
        valid_token = request.env['mail.thread']._notify_encode_link(base_link, params)
        return consteq(valid_token, str(token))

    @classmethod
    def _check_token_and_record_or_redirect(cls, model, res_id, token):
        comparison = cls._check_token(token)
        if not comparison:
            _logger.warning('Invalid token in route %s', request.httprequest.url)
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
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        # access_token and kwargs are used in the portal controller override for the Send by email or Share Link
        # to give access to the record to a recipient that has normally no access.
        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        cids = False

        # no model / res_id, meaning no possible record -> redirect to login
        if not model or not res_id or model not in request.env:
            return cls._redirect_to_messaging()

        # find the access action using sudo to have the details about the access link
        RecordModel = request.env[model]
        record_sudo = RecordModel.sudo().browse(res_id).exists()
        if not record_sudo:
            # record does not seem to exist -> redirect to login
            return cls._redirect_to_messaging()

        # the record has a window redirection: check access rights
        if uid is not None:
            if not RecordModel.with_user(uid).check_access_rights('read', raise_exception=False):
                return cls._redirect_to_messaging()
            try:
                # We need here to extend the "allowed_company_ids" to allow a redirection
                # to any record that the user can access, regardless of currently visible
                # records based on the "currently allowed companies".
                cids = request.httprequest.cookies.get('cids', str(user.company_id.id))
                cids = [int(cid) for cid in cids.split(',')]
                try:
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids).check_access_rule('read')
                except AccessError:
                    # In case the allowed_company_ids from the cookies (i.e. the last user configuration
                    # on his browser) is not sufficient to avoid an ir.rule access error, try to following
                    # heuristic:
                    # - Guess the supposed necessary company to access the record via the method
                    #   _get_mail_redirect_suggested_company
                    #   - If no company, then redirect to the messaging
                    #   - Merge the suggested company with the companies on the cookie
                    # - Make a new access test if it succeeds, redirect to the record. Otherwise, 
                    #   redirect to the messaging.
                    suggested_company = record_sudo._get_mail_redirect_suggested_company()
                    if not suggested_company:
                        raise AccessError('')
                    cids = cids + [suggested_company.id]
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids).check_access_rule('read')
            except AccessError:
                return cls._redirect_to_messaging()
            else:
                record_action = record_sudo.get_access_action(access_uid=uid)
        else:
            record_action = record_sudo.get_access_action()
            if record_action['type'] == 'ir.actions.act_url' and record_action.get('target_type') != 'public':
                url_params = {
                    'model': model,
                    'id': res_id,
                    'active_id': res_id,
                    'action': record_action.get('id'),
                }
                view_id = record_sudo.get_formview_id()
                if view_id:
                    url_params['view_id'] = view_id
                url = '/web/login?redirect=#%s' % url_encode(url_params)
                return werkzeug.utils.redirect(url)

        record_action.pop('target_type', None)
        # the record has an URL redirection: use it directly
        if record_action['type'] == 'ir.actions.act_url':
            return werkzeug.utils.redirect(record_action['url'])
        # other choice: act_window (no support of anything else currently)
        elif not record_action['type'] == 'ir.actions.act_window':
            return cls._redirect_to_messaging()

        url_params = {
            'model': model,
            'id': res_id,
            'active_id': res_id,
            'action': record_action.get('id'),
        }
        view_id = record_sudo.get_formview_id()
        if view_id:
            url_params['view_id'] = view_id

        if cids:
            url_params['cids'] = ','.join([str(cid) for cid in cids])
        url = '/web?#%s' % url_encode(url_params)
        return werkzeug.utils.redirect(url)

    @http.route('/mail/thread/data', methods=['POST'], type='json', auth='user')
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        res = {}
        thread = request.env[thread_model].with_context(active_test=False).search([('id', '=', thread_id)])
        if 'attachments' in request_list:
            res['attachments'] = thread.env['ir.attachment'].search([('res_id', '=', thread.id), ('res_model', '=', thread._name)], order='id desc')._attachment_format(commands=True)
        return res

    @http.route('/mail/read_followers', type='json', auth='user')
    def read_followers(self, res_model, res_id):
        request.env['mail.followers'].check_access_rights("read")
        request.env[res_model].check_access_rights("read")
        request.env[res_model].browse(res_id).check_access_rule("read")
        follower_recs = request.env['mail.followers'].search([('res_model', '=', res_model), ('res_id', '=', res_id)])

        followers = []
        follower_id = None
        for follower in follower_recs:
            if follower.partner_id == request.env.user.partner_id:
                follower_id = follower.id
            followers.append({
                'id': follower.id,
                'partner_id': follower.partner_id.id,
                'channel_id': follower.channel_id.id,
                'name': follower.name,
                'display_name': follower.display_name,
                'email': follower.email,
                'is_active': follower.is_active,
                # When editing the followers, the "pencil" icon that leads to the edition of subtypes
                # should be always be displayed and not only when "debug" mode is activated.
                'is_editable': True
            })
        return {
            'followers': followers,
            'subtypes': self.read_subscription_data(follower_id) if follower_id else None
        }

    @http.route('/mail/read_subscription_data', type='json', auth='user')
    def read_subscription_data(self, follower_id):
        """ Computes:
            - message_subtype_data: data about document subtypes: which are
                available, which are followed if any """
        request.env['mail.followers'].check_access_rights("read")
        follower = request.env['mail.followers'].sudo().browse(follower_id)
        follower.ensure_one()
        request.env[follower.res_model].check_access_rights("read")
        request.env[follower.res_model].browse(follower.res_id).check_access_rule("read")

        # find current model subtypes, add them to a dictionary
        subtypes = request.env['mail.message.subtype'].search([
            '&', ('hidden', '=', False),
            '|', ('res_model', '=', follower.res_model), ('res_model', '=', False)])
        followed_subtypes_ids = set(follower.subtype_ids.ids)
        subtypes_list = [{
            'name': subtype.name,
            'res_model': subtype.res_model,
            'sequence': subtype.sequence,
            'default': subtype.default,
            'internal': subtype.internal,
            'followed': subtype.id in followed_subtypes_ids,
            'parent_model': subtype.parent_id.res_model,
            'id': subtype.id
        } for subtype in subtypes]
        return sorted(subtypes_list,
                      key=lambda it: (it['parent_model'] or '', it['res_model'] or '', it['internal'], it['sequence']))

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
            res_id = int(res_id)
        return self._redirect_to_record(model, res_id, access_token, **kwargs)

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
                    status, headers, _content = request.env['ir.http'].sudo().binary_content(
                        model='res.partner', id=partner_id, field='image_128', default_mimetype='image/png')
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

    @http.route('/mail/init_messaging', type='json', auth='user')
    def mail_init_messaging(self):
        values = {
            'needaction_inbox_counter': request.env['res.partner'].get_needaction_count(),
            'starred_counter': request.env['res.partner'].get_starred_count(),
            'channel_slots': request.env['mail.channel'].channel_fetch_slot(),
            'mail_failures': request.env['mail.message'].message_fetch_failed(),
            'commands': request.env['mail.channel'].get_mention_commands(),
            'mention_partner_suggestions': request.env['res.partner'].get_static_mention_suggestions(),
            'shortcodes': request.env['mail.shortcode'].sudo().search_read([], ['source', 'substitution', 'description']),
            'menu_id': request.env['ir.model.data'].xmlid_to_res_id('mail.menu_root_discuss'),
            'moderation_counter': request.env.user.moderation_counter,
            'moderation_channel_ids': request.env.user.moderation_channel_ids.ids,
            'partner_root': request.env.ref('base.partner_root').sudo().mail_partner_format(),
            'public_partner': request.env.ref('base.public_partner').sudo().mail_partner_format(),
            'public_partners': [partner.mail_partner_format() for partner in request.env.ref('base.group_public').sudo().with_context(active_test=False).users.partner_id],
            'current_partner': request.env.user.partner_id.mail_partner_format(),
            'current_user_id': request.env.user.id,
        }
        return values

    @http.route('/mail/get_partner_info', type='json', auth='user')
    def message_partner_info_from_emails(self, model, res_ids, emails, link_mail=False):
        records = request.env[model].browse(res_ids)
        try:
            records.check_access_rule('read')
            records.check_access_rights('read')
        except:
            return []
        return records._message_partner_info_from_emails(emails, link_mail=link_mail)

    @http.route('/mail/get_suggested_recipients', type='json', auth='user')
    def message_get_suggested_recipients(self, model, res_ids):
        records = request.env[model].browse(res_ids)
        try:
            records.check_access_rule('read')
            records.check_access_rights('read')
        except:
            return {}
        return records._message_get_suggested_recipients()
