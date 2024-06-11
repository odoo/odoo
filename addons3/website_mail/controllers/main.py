# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import http
from odoo.http import request


class WebsiteMail(http.Controller):

    @http.route(['/website_mail/follow'], type='json', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        # TDE FIXME: check this method with new followers
        res_id = int(id)
        is_follower = message_is_follower == 'on'
        record = request.env[object].browse(res_id).exists()
        if not record:
            return False

        record.check_access_rights('read')
        record.check_access_rule('read')

        # search partner_id
        if request.env.user != request.website.user_id:
            partner_ids = request.env.user.partner_id.ids
        else:
            # mail_thread method
            partner_ids = [p.id for p in request.env['mail.thread'].sudo()._mail_find_partner_from_emails([email], records=record.sudo()) if p]
            if not partner_ids or not partner_ids[0]:
                name = email.split('@')[0]
                partner_ids = request.env['res.partner'].sudo().create({'name': name, 'email': email}).ids
        # add or remove follower
        if is_follower:
            record.sudo().message_unsubscribe(partner_ids)
            return False
        else:
            # add partner to session
            request.session['partner_id'] = partner_ids[0]
            record.sudo().message_subscribe(partner_ids)
            return True

    @http.route(['/website_mail/is_follower'], type='json', auth="public", website=True)
    def is_follower(self, records, **post):
        """ Given a list of `models` containing a list of res_ids, return
            the res_ids for which the user is follower and some practical info.

            :param records: dict of models containing record IDS, eg: {
                    'res.model': [1, 2, 3..],
                    'res.model2': [1, 2, 3..],
                    ..
                }

            :returns: [
                    {'is_user': True/False, 'email': 'admin@yourcompany.example.com'},
                    {'res.model': [1, 2], 'res.model2': [1]}
                ]
        """
        user = request.env.user
        partner = None
        public_user = request.website.user_id
        if user != public_user:
            partner = request.env.user.partner_id
        elif request.session.get('partner_id'):
            partner = request.env['res.partner'].sudo().browse(request.session.get('partner_id'))

        res = defaultdict(list)
        if partner:
            for model in records:
                mail_followers_ids = request.env['mail.followers'].sudo()._read_group([
                    ('res_model', '=', model),
                    ('res_id', 'in', records[model]),
                    ('partner_id', '=', partner.id)
                ], ['res_id'])
                # `_read_group` will filter out the ones not matching the domain
                res[model].extend(res_id for [res_id] in mail_followers_ids)

        return [{
            'is_user': user != public_user,
            'email': partner.email if partner else "",
        }, res]
