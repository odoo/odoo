# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug.urls import url_encode
from werkzeug.exceptions import NotFound, Unauthorized

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.mail.controllers.discuss.public_page import PublicPageController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store

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
                        raise AccessError('')
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
            return request.redirect(record_action['url'])
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
            raise Unauthorized()

        # sudo: public user can access some relational fields of mail.message
        if message.sudo()._filter_empty():
            raise NotFound()
        if not request.env.user._is_internal():
            thread = request.env[message.model].search([('id', '=', message.res_id)])
            if message.model == 'discuss.channel':
                store = Store({'isChannelTokenSecret': True})
                store.add(thread, {'highlightMessage': Store.one(message, only_id=True)})
                return PublicPageController()._response_discuss_channel_invitation(store, thread)
            elif hasattr(thread, '_get_share_url'):
                return request.redirect(thread._get_share_url(share_token=False))
            else:
                raise Unauthorized()

        if message.model == 'discuss.channel':
            url = f'/odoo/action-mail.action_discuss?active_id={message.res_id}&highlight_message_id={message_id}'
        else:
            # @see commit c63d14a0485a553b74a8457aee158384e9ae6d3f
            # @see router.js: heuristics to discrimate a model name from an action path
            # is the presence of dots, or the prefix m- for models
            model_in_url = model if "." in (model := message.model) else "m-" + model
            url = f'/odoo/{model_in_url}/{message.res_id}?highlight_message_id={message_id}'
        return request.redirect(url)
