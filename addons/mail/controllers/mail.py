# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug.urls import url_encode

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MailController(http.Controller):
    _cp_path = '/mail'

    @classmethod
    def _redirect_to_messaging(cls):
        url = '/web#%s' % url_encode({'action': 'mail.action_discuss'})
        return request.redirect(url)

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
        cids = []

        # no model / res_id, meaning no possible record -> redirect to login
        if not model or not res_id or model not in request.env:
            return cls._redirect_to_messaging()

        # find the access action using sudo to have the details about the access link
        RecordModel = request.env[model]
        record_sudo = RecordModel.sudo().browse(res_id).exists()
        if not record_sudo:
            # record does not seem to exist -> redirect to login
            return cls._redirect_to_messaging()

        suggested_company = record_sudo._get_mail_redirect_suggested_company()
        # the record has a window redirection: check access rights
        if uid is not None:
            if not RecordModel.with_user(uid).check_access_rights('read', raise_exception=False):
                return cls._redirect_to_messaging()
            try:
                # We need here to extend the "allowed_company_ids" to allow a redirection
                # to any record that the user can access, regardless of currently visible
                # records based on the "currently allowed companies".
                cids_str = request.httprequest.cookies.get('cids', str(user.company_id.id))
                cids = [int(cid) for cid in cids_str.split(',')]
                try:
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids).check_access_rule('read')
                except AccessError:
                    # In case the allowed_company_ids from the cookies (i.e. the last user configuration
                    # on their browser) is not sufficient to avoid an ir.rule access error, try to following
                    # heuristic:
                    # - Guess the supposed necessary company to access the record via the method
                    #   _get_mail_redirect_suggested_company
                    #   - If no company, then redirect to the messaging
                    #   - Merge the suggested company with the companies on the cookie
                    # - Make a new access test if it succeeds, redirect to the record. Otherwise, 
                    #   redirect to the messaging.
                    if not suggested_company:
                        raise AccessError('')
                    cids = cids + [suggested_company.id]
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids).check_access_rule('read')
            except AccessError:
                return cls._redirect_to_messaging()
            else:
                record_action = record_sudo._get_access_action(access_uid=uid)
        else:
            record_action = record_sudo._get_access_action()
            if suggested_company:
                cids = [suggested_company.id]
            if record_action['type'] == 'ir.actions.act_url' and record_action.get('target_type') != 'public':
                url_params = {
                    'model': model,
                    'id': res_id,
                    'active_id': res_id,
                    'action': record_action.get('id'),
                }
                if cids:
                    url_params['cids'] = cids[0]
                view_id = record_sudo.get_formview_id()
                if view_id:
                    url_params['view_id'] = view_id
                url = '/web/login?redirect=#%s' % url_encode(url_params)
                return request.redirect(url)

        record_action.pop('target_type', None)
        # the record has an URL redirection: use it directly
        if record_action['type'] == 'ir.actions.act_url':
            return request.redirect(record_action['url'])
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
            try:
                record.check_access_rights('read')
                record.check_access_rule('read')
            except AccessError:
                display_link = False

        return request.render('mail.message_document_unfollowed', {
            'name': record_sudo.display_name,
            'model_name': request.env['ir.model'].sudo()._get(model).display_name,
            'access_url': record._notify_get_action_link('view', model=model, res_id=res_id) if display_link else False,
        })
