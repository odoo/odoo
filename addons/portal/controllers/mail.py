# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
from werkzeug import urls
from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.tools import consteq, plaintext2html
from odoo.addons.mail.controllers.main import MailController
from odoo.exceptions import AccessError


def _has_token_access(res_model, res_id, token=''):
    record = request.env[res_model].browse(res_id).sudo()
    token_field = request.env[res_model]._mail_post_token_field
    return (token and record and consteq(record[token_field], token))


def _message_post_helper(res_model='', res_id=None, message='', token='', nosubscribe=True, **kw):
    """ Generic chatter function, allowing to write on *any* object that inherits mail.thread.
        If a token is specified, all logged in users will be able to write a message regardless
        of access rights; if the user is the public user, the message will be posted under the name
        of the partner_id of the object (or the public user if there is no partner_id on the object).

        :param string res_model: model name of the object
        :param int res_id: id of the object
        :param string message: content of the message

        optional keywords arguments:
        :param string token: access token if the object's model uses some kind of public access
                             using tokens (usually a uuid4) to bypass access rules
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    record = request.env[res_model].browse(res_id)
    author_id = request.env.user.partner_id.id if request.env.user.partner_id else False
    if token:
        access_as_sudo = _has_token_access(res_model, res_id, token=token)
        if access_as_sudo:
            record = record.sudo()
            if request.env.user._is_public():
                if kw.get('pid') and consteq(kw.get('hash'), record._sign_token(int(kw.get('pid')))):
                    author_id = kw.get('pid')
                else:
                    # TODO : After adding the pid and sign_token in access_url when send invoice by email, remove this line
                    # TODO : Author must be Public User (to rename to 'Anonymous')
                    author_id = record.partner_id.id if hasattr(record, 'partner_id') and record.partner_id.id else author_id
            else:
                if not author_id:
                    raise NotFound()
        else:
            raise Forbidden()
    kw.pop('csrf_token', None)
    kw.pop('attachment_ids', None)

    email_from = None
    if author_id and 'email_from' not in kw:
        partner = request.env['res.partner'].sudo().browse(author_id)
        email_from = partner.email_formatted if partner.email else None

    message_post_args = dict(
        body=message,
        message_type=kw.pop('message_type', "comment"),
        subtype=kw.pop('subtype', "mt_comment"),
        author_id=author_id,
        **kw
    )

    # This is necessary as mail.message checks the presence
    # of the key to compute its default email from
    if email_from:
        message_post_args['email_from'] = email_from

    return record.with_context(mail_create_nosubscribe=nosubscribe).message_post(**message_post_args)


class PortalChatter(http.Controller):

    @http.route(['/mail/chatter_post'], type='http', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, **kw):
        url = request.httprequest.referrer
        if message:
            # message is received in plaintext and saved in html
            message = plaintext2html(message)
            _message_post_helper(res_model, int(res_id), message, **kw)
            url = url + "#discussion"
        return request.redirect(url)

    @http.route('/mail/chatter_init', type='json', auth='public', website=True)
    def portal_chatter_init(self, res_model, res_id, domain=False, limit=False, **kwargs):
        is_user_public = request.env.user.has_group('base.group_public')
        message_data = self.portal_message_fetch(res_model, res_id, domain=domain, limit=limit, **kwargs)
        display_composer = False
        if kwargs.get('allow_composer'):
            display_composer = kwargs.get('token') or not is_user_public
        return {
            'messages': message_data['messages'],
            'options': {
                'message_count': message_data['message_count'],
                'is_user_public': is_user_public,
                'is_user_publisher': request.env.user.has_group('website.group_website_publisher'),
                'display_composer': display_composer,
                'partner_id': request.env.user.partner_id.id
            }
        }

    @http.route('/mail/chatter_fetch', type='json', auth='public', website=True)
    def portal_message_fetch(self, res_model, res_id, domain=False, limit=10, offset=0, **kw):
        if not domain:
            domain = []
        # Only search into website_message_ids, so apply the same domain to perform only one search
        # extract domain from the 'website_message_ids' field
        field_domain = request.env[res_model]._fields['website_message_ids'].domain
        if callable(field_domain):
            field_domain = field_domain(request.env[res_model])
        domain = expression.AND([domain, field_domain, [('res_id', '=', res_id)]])

        # Check access
        Message = request.env['mail.message']
        if kw.get('token'):
            access_as_sudo = _has_token_access(res_model, res_id, token=kw.get('token'))
            if not access_as_sudo:  # if token is not correct, raise Forbidden
                raise Forbidden()
            # Non-employee see only messages with not internal subtype (aka, no internal logs)
            if not request.env['res.users'].has_group('base.group_user'):
                domain = expression.AND([Message._non_employee_message_domain(), domain])
            Message = request.env['mail.message'].sudo()
        return {
            'messages': Message.search(domain, limit=limit, offset=offset).portal_message_format(),
            'message_count': Message.search_count(domain)
        }


class MailController(MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        """ If the current user doesn't have access to the document, but provided
        a valid access token, redirect him to the front-end view.
        If the partner_id and hash parameters are given, add those parameters to the redirect url
        to authentify the recipient in the chatter, if any.

        :param model: the model name of the record that will be visualized
        :param res_id: the id of the record
        :param access_token: token that gives access to the record
            bypassing the rights and rules restriction of the user.
        :param kwargs: Typically, it can receive a partner_id and a hash (sign_token).
            If so, those two parameters are used to authentify the recipient in the chatter, if any.
        :return:
        """
        if issubclass(type(request.env[model]), request.env.registry['portal.mixin']):
            uid = request.session.uid or request.env.ref('base.public_user').id
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            try:
                record_sudo.sudo(uid).check_access_rights('read')
                record_sudo.sudo(uid).check_access_rule('read')
            except AccessError:
                if record_sudo.access_token and access_token and consteq(record_sudo.access_token, access_token):
                    record_action = record_sudo.with_context(force_website=True).get_access_action()
                    if record_action['type'] == 'ir.actions.act_url':
                        pid = kwargs.get('pid')
                        hash = kwargs.get('hash')
                        url = record_action['url']
                        if pid and hash:
                            url = urls.url_parse(url)
                            url_params = url.decode_query()
                            url_params.update([("pid", pid), ("hash", hash)])
                            url = url.replace(query=urls.url_encode(url_params)).to_url()
                        return werkzeug.utils.redirect(url)
        return super(MailController, cls)._redirect_to_record(model, res_id, access_token=access_token)
