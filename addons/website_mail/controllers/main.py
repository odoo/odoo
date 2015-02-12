# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class WebsiteMail(http.Controller):

    @http.route(['/website_mail/follow'], type='json', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        Partner = request.env['res.partner']
           
        _id = int(id)
        _message_is_follower = message_is_follower == 'on'
        _object = request.env[object]

        # search partner_id
        public_id = request.website.user_id.id
        if request.uid != public_id:
            partner_ids = request.env.user.partner_id.ids
        else:
            # mail_thread method
            partner_ids = _object.sudo()._find_partner_from_emails(_id, [email], check_followers=True)
            if not partner_ids or not partner_ids[0]:
                partner_ids = Partner.sudo().create({'name': email, 'email': email}).ids
        # add or remove follower
        obj = _object.browse([_id])
        if _message_is_follower:
            obj.check_access_rule('read')
            obj.sudo().message_unsubscribe(partner_ids)
            return False
        else:
            obj.check_access_rule('read')
            # add partner to session
            request.session['partner_id'] = partner_ids[0]
            obj.sudo().message_subscribe(partner_ids)
            return True

    @http.route(['/website_mail/is_follower'], type='json', auth="public", website=True)
    def call(self, model, id, **post):
        id = int(id)
        Partner = request.env['res.partner']
        Obj = request.env[model]
        partner_id = None
        public_id = request.website.user_id.id
        if request.uid != public_id:
            partner_id = request.env.user.sudo().partner_id
        elif request.session.get('partner_id'):
            partner_id = Partner.sudo().browse(request.session.get('partner_id'))
        email = partner_id and partner_id.email or ""

        values = {
            'is_user': request.uid != public_id,
            'email': email,
            'is_follower': False,
            'alias_name': False,
        }
        if not model:
            return values
        obj_ids = Obj.sudo().browse([id])
        
        if obj_ids.exists():
            if partner_id:
                values['is_follower'] = len(
                    request.env['mail.followers'].sudo().search([('res_model', '=', model),
                                                                 ('res_id', '=', obj_ids[0].id),
                                                                 ('partner_id', '=', partner_id.id)])) == 1
        return values
