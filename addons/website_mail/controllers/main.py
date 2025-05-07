# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import http
from odoo.http import request


class WebsiteMail(http.Controller):

    @http.route(['/website_mail/follow'], type='jsonrpc', auth="public", website=True)
    def website_message_subscribe(self, id=0, object=None, message_is_follower="on", email=False, **post):
        # TDE FIXME: check this method with new followers
        res_id = int(id)
        is_follower = message_is_follower == 'on'
        record = request.env[object].browse(res_id).exists()
        if not record:
            return False

        record.check_access('read')

        # search partner_id
        if request.env.user != request.website.user_id:
            partner_id = request.env.user.partner_id.id
        else:
            # mail_thread method
            try:
                self.env['ir.http']._verify_request_recaptcha_token('website_mail_follow')
            except Exception:
                no_create = True
            else:
                no_create = False
            thread_record = record if hasattr(record, "_partner_find_from_emails_single") else request.env['mail.thread']
            partner_id = thread_record.sudo()._partner_find_from_emails_single([email], no_create=no_create).id

        if not is_follower:
            # add partner to session
            request.session['partner_id'] = partner_id

        self._subscribe_partner(record, partner_id, not is_follower)
        return not is_follower

    def _subscribe_partner(self, record, partner_id, subscribe):
        """Subscribe the given partner on the record."""
        if subscribe:
            record.sudo().message_subscribe([partner_id])
            return

        record.sudo().message_unsubscribe([partner_id])

    @http.route(['/website_mail/is_follower'], type='jsonrpc', auth="public", website=True, readonly=True)
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
        public_user = request.website.user_id
        partner = self._get_user_partner()
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
            'is_user': request.env.user != public_user,
            'email': partner.email if partner else "",
        }, res]

    def _get_user_partner(self):
        """Return the effective partner of the current user."""
        if request.env.user != request.website.user_id:
            return request.env.user.partner_id
        if pid := request.session.get('partner_id'):
            return request.env['res.partner'].sudo().browse(pid)
        return None
