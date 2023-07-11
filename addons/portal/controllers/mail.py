# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls
from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.tools import consteq, plaintext2html
from odoo.addons.mail.controllers import mail
from odoo.exceptions import AccessError


def _check_special_access(res_model, res_id, token='', _hash='', pid=False):
    record = request.env[res_model].browse(res_id).sudo()
    if _hash and pid:  # Signed Token Case: hash implies token is signed by partner pid
        return consteq(_hash, record._sign_token(pid))
    elif token:  # Token Case: token is the global one of the document
        token_field = request.env[res_model]._mail_post_token_field
        return (token and record and consteq(record[token_field], token))
    else:
        raise Forbidden()


def _message_post_helper(res_model, res_id, message, token='', _hash=False, pid=False, nosubscribe=True, **kw):
    """ Generic chatter function, allowing to write on *any* object that inherits mail.thread. We
        distinguish 2 cases:
            1/ If a token is specified, all logged in users will be able to write a message regardless
            of access rights; if the user is the public user, the message will be posted under the name
            of the partner_id of the object (or the public user if there is no partner_id on the object).

            2/ If a signed token is specified (`hash`) and also a partner_id (`pid`), all post message will
            be done under the name of the partner_id (as it is signed). This should be used to avoid leaking
            token to all users.

        Required parameters
        :param string res_model: model name of the object
        :param int res_id: id of the object
        :param string message: content of the message

        Optional keywords arguments:
        :param string token: access token if the object's model uses some kind of public access
                             using tokens (usually a uuid4) to bypass access rules
        :param string hash: signed token by a partner if model uses some token field to bypass access right
                            post messages.
        :param string pid: identifier of the res.partner used to sign the hash
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    record = request.env[res_model].browse(res_id)

    # check if user can post with special token/signed token. The "else" will try to post message with the
    # current user access rights (_mail_post_access use case).
    if token or (_hash and pid):
        pid = int(pid) if pid else False
        if _check_special_access(res_model, res_id, token=token, _hash=_hash, pid=pid):
            record = record.sudo()
        else:
            raise Forbidden()
    else:  # early check on access to avoid useless computation
        record.check_access_rights('read')
        record.check_access_rule('read')

    # deduce author of message
    author_id = request.env.user.partner_id.id if request.env.user.partner_id else False

    # Signed Token Case: author_id is forced
    if _hash and pid:
        author_id = pid
    # Token Case: author is document customer (if not logged) or itself even if user has not the access
    elif token:
        if request.env.user._is_public():
            # TODO : After adding the pid and sign_token in access_url when send invoice by email, remove this line
            # TODO : Author must be Public User (to rename to 'Anonymous')
            author_id = record.partner_id.id if hasattr(record, 'partner_id') and record.partner_id.id else author_id
        else:
            if not author_id:
                raise NotFound()

    email_from = None
    if author_id and 'email_from' not in kw:
        partner = request.env['res.partner'].sudo().browse(author_id)
        email_from = partner.email_formatted if partner.email else None

    message_post_args = dict(
        body=message,
        message_type=kw.pop('message_type', "comment"),
        subtype_xmlid=kw.pop('subtype_xmlid', "mail.mt_comment"),
        author_id=author_id,
        **kw
    )

    # This is necessary as mail.message checks the presence
    # of the key to compute its default email from
    if email_from:
        message_post_args['email_from'] = email_from

    return record.with_context(mail_create_nosubscribe=nosubscribe).message_post(**message_post_args)


class PortalChatter(http.Controller):

    def _portal_post_filter_params(self):
        return ['token', 'pid']

    def _portal_post_check_attachments(self, attachment_ids, attachment_tokens):
        request.env['ir.attachment'].browse(attachment_ids)._check_attachments_access(attachment_tokens)

    def _portal_post_has_content(self, res_model, res_id, message, attachment_ids=None, **kw):
        """ Tells if we can effectively post on the model based on content. """
        return bool(message) or bool(attachment_ids)

    @http.route(['/mail/chatter_post'], type='json', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, attachment_ids=None, attachment_tokens=None, **kw):
        """Create a new `mail.message` with the given `message` and/or `attachment_ids` and return new message values.

        The message will be associated to the record `res_id` of the model
        `res_model`. The user must have access rights on this target document or
        must provide valid identifiers through `kw`. See `_message_post_helper`.
        """
        if not self._portal_post_has_content(res_model, res_id, message,
                                             attachment_ids=attachment_ids, attachment_tokens=attachment_tokens,
                                             **kw):
            return

        res_id = int(res_id)

        self._portal_post_check_attachments(attachment_ids or [], attachment_tokens or [])

        result = {'default_message': message}
        # message is received in plaintext and saved in html
        if message:
            message = plaintext2html(message)
        post_values = {
            'res_model': res_model,
            'res_id': res_id,
            'message': message,
            'send_after_commit': False,
            'attachment_ids': False,  # will be added afterward
        }
        post_values.update((fname, kw.get(fname)) for fname in self._portal_post_filter_params())
        post_values['_hash'] = kw.get('hash')
        message = _message_post_helper(**post_values)
        result.update({'default_message_id': message.id})

        if attachment_ids:
            # _message_post_helper already checks for pid/hash/token -> use message
            # environment to keep the sudo mode when activated
            record = message.env[res_model].browse(res_id)
            attachments = record._process_attachments_for_post(
                [], attachment_ids,
                {'res_id': res_id, 'model': res_model}
            )
            # sudo write the attachment to bypass the read access verification in
            # mail message
            if attachments.get('attachment_ids'):
                message.sudo().write(attachments)

            result.update({'default_attachment_ids': message.attachment_ids.sudo().read(['id', 'name', 'mimetype', 'file_size', 'access_token'])})
        return result

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
                'is_user_employee': request.env.user._is_internal(),
                'is_user_publisher': request.env.user.has_group('website.group_website_restricted_editor'),
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
        model = request.env[res_model]
        field = model._fields['website_message_ids']
        field_domain = field.get_domain_list(model)
        domain = expression.AND([
            domain,
            field_domain,
            [('res_id', '=', res_id), '|', ('body', '!=', ''), ('attachment_ids', '!=', False)]
        ])

        # Check access
        Message = request.env['mail.message']
        if kw.get('token'):
            access_as_sudo = _check_special_access(res_model, res_id, token=kw.get('token'))
            if not access_as_sudo:  # if token is not correct, raise Forbidden
                raise Forbidden()
            # Non-employee see only messages with not internal subtype (aka, no internal logs)
            if not request.env['res.users'].has_group('base.group_user'):
                domain = expression.AND([Message._get_search_domain_share(), domain])
            Message = request.env['mail.message'].sudo()
        return {
            'messages': Message.search(domain, limit=limit, offset=offset).portal_message_format(options=kw),
            'message_count': Message.search_count(domain)
        }

    @http.route(['/mail/update_is_internal'], type='json', auth="user", website=True)
    def portal_message_update_is_internal(self, message_id, is_internal):
        message = request.env['mail.message'].browse(int(message_id))
        message.write({'is_internal': is_internal})
        return message.is_internal


class MailController(mail.MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        """ If the current user doesn't have access to the document, but provided
        a valid access token, redirect them to the front-end view.
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
        # no model / res_id, meaning no possible record -> direct skip to super
        if not model or not res_id or model not in request.env:
            return super(MailController, cls)._redirect_to_record(model, res_id, access_token=access_token, **kwargs)

        if issubclass(type(request.env[model]), request.env.registry['portal.mixin']):
            uid = request.session.uid or request.env.ref('base.public_user').id
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            try:
                record_sudo.with_user(uid).check_access_rights('read')
                record_sudo.with_user(uid).check_access_rule('read')
            except AccessError:
                if record_sudo.access_token and access_token and consteq(record_sudo.access_token, access_token):
                    record_action = record_sudo._get_access_action(force_website=True)
                    if record_action['type'] == 'ir.actions.act_url':
                        pid = kwargs.get('pid')
                        hash = kwargs.get('hash')
                        url = record_action['url']
                        if pid and hash:
                            url = urls.url_parse(url)
                            url_params = url.decode_query()
                            url_params.update([("pid", pid), ("hash", hash)])
                            url = url.replace(query=urls.url_encode(url_params)).to_url()
                        return request.redirect(url)
        return super(MailController, cls)._redirect_to_record(model, res_id, access_token=access_token, **kwargs)

    # Add website=True to support the portal layout
    @http.route('/mail/unfollow', type='http', website=True)
    def mail_action_unfollow(self, model, res_id, pid, token, **kwargs):
        return super().mail_action_unfollow(model, res_id, pid, token, **kwargs)
