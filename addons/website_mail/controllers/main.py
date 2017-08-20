# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug.exceptions import NotFound, Forbidden

from odoo import http
from odoo.http import request
from odoo.tools import consteq


def _special_access_object(res_model, res_id, token='', token_field=''):
    record = request.env[res_model].browse(res_id).sudo()
    if token and record and getattr(record, token_field, None) and consteq(getattr(record, token_field), token):
        return True
    return False

def _message_post_helper(res_model='', res_id=None, message='', token='', token_field='token', nosubscribe=True, **kw):
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
        :param string token_field: name of the field that contains the token on the object (defaults to 'token')
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    record = request.env[res_model].browse(res_id)
    author_id = request.env.user.partner_id.id if request.env.user.partner_id else False
    if token_field and token:
        access_as_sudo = _special_access_object(res_model, res_id, token=token, token_field=token_field)
        if access_as_sudo:
            record = record.sudo()
            if request.env.user == request.env.ref('base.public_user'):
                author_id = record.partner_id.id if hasattr(record, 'partner_id') else author_id
            else:
                if not author_id:
                    raise NotFound()
        else:
            raise Forbidden()
    kw.pop('csrf_token', None)
    return record.with_context(mail_create_nosubscribe=nosubscribe).message_post(body=message,
                                                                                   message_type=kw.pop('message_type', "comment"),
                                                                                   subtype=kw.pop('subtype', "mt_comment"),
                                                                                   author_id=author_id,
                                                                                   **kw)


class WebsiteMail(http.Controller):

    @http.route(['/website_mail/follow'], type='json', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        # TDE FIXME: check this method with new followers
        res_id = int(id)
        is_follower = message_is_follower == 'on'
        record = request.env[object].browse(res_id)

        # search partner_id
        if request.env.user != request.website.user_id:
            partner_ids = request.env.user.partner_id.ids
        else:
            # mail_thread method
            partner_ids = record.sudo()._find_partner_from_emails([email], check_followers=True)
            if not partner_ids or not partner_ids[0]:
                name = email.split('@')[0]
                partner_ids = request.env['res.partner'].sudo().create({'name': name, 'email': email}).ids
        # add or remove follower
        if is_follower:
            record.check_access_rule('read')
            record.sudo().message_unsubscribe(partner_ids)
            return False
        else:
            record.check_access_rule('read')
            # add partner to session
            request.session['partner_id'] = partner_ids[0]
            record.sudo().message_subscribe(partner_ids)
            return True

    @http.route(['/website_mail/is_follower'], type='json', auth="public", website=True)
    def is_follower(self, model, res_id, **post):
        user = request.env.user
        partner = None
        public_user = request.website.user_id
        if user != public_user:
            partner = request.env.user.partner_id
        elif request.session.get('partner_id'):
            partner = request.env['res.partner'].sudo().browse(request.session.get('partner_id'))

        values = {
            'is_user': user != public_user,
            'email': partner.email if partner else "",
            'is_follower': False,
            'alias_name': False,
        }

        record = request.env[model].sudo().browse(int(res_id))
        if record and partner:
            values['is_follower'] = bool(request.env['mail.followers'].search_count([
                ('res_model', '=', model),
                ('res_id', '=', record.id),
                ('partner_id', '=', partner.id)
            ]))
        return values

    @http.route(['/website_mail/post/post'], type='http', methods=['POST'], auth='public', website=True)
    def website_chatter_post(self, res_model, res_id, message, **kw):
        url = request.httprequest.referrer
        if message:
            _message_post_helper(res_model, int(res_id), message, **kw)
            url = url + "#discussion"
        return request.redirect(url)

    @http.route('/website_mail/init', type='json', auth='public', website=True)
    def website_chatter_init(self, res_model, res_id, domain=False, limit=False, **kwargs):
        is_user_public = bool(request.env.user == request.website.user_id)
        message_data = self.website_message_fetch(res_model, res_id, domain=domain, limit=limit, **kwargs)
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

    @http.route('/website_mail/fetch', type='json', auth='public', website=True)
    def website_message_fetch(self, res_model, res_id, domain=False, limit=10, offset=0, **kw):
        if not domain:
            domain = []
        # Only search into website_message_ids, so apply the same domain to perform only one search
        # extract domain from the 'website_message_ids' field
        field_domain = request.env[res_model]._fields['website_message_ids'].domain
        domain += field_domain(request.env[res_model]) if callable(field_domain) else field_domain
        domain += [('res_id', '=', res_id)]
        # Check access
        Message = request.env['mail.message']
        if kw.get('token'):
            access_as_sudo = _special_access_object(res_model, res_id, token=kw.get('token'), token_field=kw.get('token_field'))
            if not access_as_sudo:  # if token is not correct, raise Forbidden
                raise Forbidden()
            Message = request.env['mail.message'].sudo()
        return {
            'messages': Message.search(domain, limit=limit, offset=offset).website_message_format(),
            'message_count': Message.search_count(domain)
        }
