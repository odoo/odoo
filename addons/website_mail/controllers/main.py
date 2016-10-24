# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from hashlib import sha1
from time import time
from werkzeug.exceptions import NotFound

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request


def object_shasign(record=False, res_model='', res_id=None, **kw):
    """ Generate a sha signature using the current time, database secret and the
    record object or the res_model and res_id parameters
        Return the sha signature and the time of generation in a tuple"""
    secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
    shasign = False
    timestamp = int(time())
    if record:
        shasign = sha1('%s%s%s%s' % (record._model, record.id, secret, timestamp)).hexdigest()
    elif res_model and res_id:
        shasign = sha1('%s%s%s%s' % (res_model, res_id, secret, timestamp)).hexdigest()
    return (shasign, timestamp)


def _message_post_helper(res_model='', res_id=None, message='', token='', token_field='token', sha_in='', sha_time=None, nosubscribe=True, **kw):
    """ Generic chatter function, allowing to write on *any* object that inherits mail.thread.
        If a token or a shasign is specified, all logged in users will be able to write a message regardless
        of access rights; if the user is the public user, the message will be posted under the name
        of the partner_id of the object (or the public user if there is no partner_id on the object).

        :param string res_model: model name of the object
        :param int res_id: id of the object
        :param string message: content of the message

        optional keywords arguments:
        :param string token: access token if the object's model uses some kind of public access
                             using tokens (usually a uuid4) to bypass access rules
        :param string token_field: name of the field that contains the token on the object (defaults to 'token')
        :param string sha_in: sha1 hash of the string composed of res_model, res_id and the dabase secret in ir.config_parameter
                               if you wish to allow public users to write on the object with some security but you don't want
                               to add a token field on the object, the sha-sign prevents public users from writing to any other
                               object that the one specified by res_model and res_id
                               to generate the shasign, you can import the function object_shasign from this file in your controller
        :param str sha_time: timestamp of sha signature generation (signatures are valid for 24h)
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    res = request.env[res_model].browse(res_id)
    author_id = request.env.user.partner_id.id
    if token and res and token == getattr(res.sudo(), token_field, None):
        res = res.sudo()
        if request.env.user == request.env['ir.model.data'].xmlid_to_object('base.public_user'):
            author_id = (res.partner_id and res.partner_id.id) if hasattr(res, 'partner_id') else author_id
        else:
            author_id = request.env.user.partner_id and request.env.user.partner_id.id
            if not author_id:
                raise NotFound()
    elif sha_in:
        timestamp = int(sha_time)
        secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        shasign = sha1('%s%s%s%s' % (res_model, res_id, secret, timestamp))
        if sha_in == shasign.hexdigest() and int(time()) < timestamp + 3600 * 24:
            res = res.sudo()
        else:
            raise NotFound()
    kw.pop('csrf_token', None)
    return res.with_context({'mail_create_nosubscribe': nosubscribe}).message_post(body=message,
                                                                                   message_type=kw.pop('message_type', False) or "comment",
                                                                                   subtype=kw.pop('subtype', False) or "mt_comment",
                                                                                   author_id=author_id,
                                                                                   **kw)

class WebsiteMail(http.Controller):

    @http.route(['/website_mail/follow'], type='json', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        # TDE FIXME: check this method with new followers
        cr, uid, context = request.cr, request.uid, request.context

        partner_obj = request.registry['res.partner']
        user_obj = request.registry['res.users']

        _id = int(id)
        _message_is_follower = message_is_follower == 'on'
        _object = request.registry[object]

        # search partner_id
        public_id = request.website.user_id.id
        if uid != public_id:
            partner_ids = [user_obj.browse(cr, uid, uid, context).partner_id.id]
        else:
            # mail_thread method
            partner_ids = _object._find_partner_from_emails(
                cr, SUPERUSER_ID, [_id], [email], context=context, check_followers=True)
            if not partner_ids or not partner_ids[0]:
                name = email.split('@')[0]
                partner_ids = [partner_obj.create(cr, SUPERUSER_ID, {'name': name, 'email': email}, context=context)]

        # add or remove follower
        if _message_is_follower:
            _object.check_access_rule(cr, uid, [_id], 'read', context)
            _object.message_unsubscribe(cr, SUPERUSER_ID, [_id], partner_ids, context=context)
            return False
        else:
            _object.check_access_rule(cr, uid, [_id], 'read', context)
            # add partner to session
            request.session['partner_id'] = partner_ids[0]
            _object.message_subscribe(cr, SUPERUSER_ID, [_id], partner_ids, context=context)
            return True

    @http.route(['/website_mail/is_follower'], type='json', auth="public", website=True)
    def call(self, model, id, **post):
        id = int(id)
        cr, uid, context = request.cr, request.uid, request.context

        partner_obj = request.registry.get('res.partner')
        users_obj = request.registry.get('res.users')
        obj = request.registry.get(model)

        partner_id = None
        public_id = request.website.user_id.id
        if uid != public_id:
            partner_id = users_obj.browse(cr, SUPERUSER_ID, uid, context).partner_id
        elif request.session.get('partner_id'):
            partner_id = partner_obj.browse(cr, SUPERUSER_ID, request.session.get('partner_id'), context)
        email = partner_id and partner_id.email or ""

        values = {
            'is_user': uid != public_id,
            'email': email,
            'is_follower': False,
            'alias_name': False,
        }

        if not obj:
            return values
        obj_ids = obj.exists(cr, SUPERUSER_ID, [id], context=context)
        if obj_ids:
            if partner_id:
                values['is_follower'] = len(
                    request.registry['mail.followers'].search(
                        cr, SUPERUSER_ID, [
                            ('res_model', '=', model),
                            ('res_id', '=', obj_ids[0]),
                            ('partner_id', '=', partner_id.id)
                        ], context=context)) == 1
        return values

    @http.route(['/website_mail/post/json'], type='json', auth='public', website=True)
    def chatter_json(self, res_model='', res_id=None, message='', **kw):
        res_id = int(res_id)
        try:
            msg = _message_post_helper(res_model, res_id, message, **kw)
            data = {
                'id': msg.id,
                'body': msg.body,
                'date': msg.date,
                'author': msg.author_id.name,
                'image_url': '/mail/%s/%s/avatar/%s' % (msg.model, msg.res_id, msg.author_id.id)
            }
            return data
        except Exception:
            return False

    @http.route(['/website_mail/post/post'], type='http', methods=['POST'], auth='public', website=True)
    def chatter_post(self, res_model='', res_id=None, message='', redirect=None, **kw):
        res_id = int(res_id)
        url = request.httprequest.referrer
        if message:
            message = _message_post_helper(res_model, res_id, message, **kw)
            url = url + "#message-%s" % (message.id,)
        return request.redirect(url)
