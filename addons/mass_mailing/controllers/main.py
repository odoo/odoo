# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

import werkzeug
from odoo import _, exceptions, http
from odoo.http import route, request
from odoo.tools import consteq


class MassMailController(http.Controller):

    @http.route(['/unsubscribe_from_list'], type='http', website=True, multilang=False, auth='public')
    def unsubscribe_placeholder_link(self, **post):
        """Dummy route so placeholder is not prefixed by language, MUST have multilang=False"""
        raise werkzeug.exceptions.NotFound()

    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='none')
    def track_mail_open(self, mail_id, **post):
        """ Email tracking. """
        request.env['mail.mail.statistics'].sudo().set_opened(mail_mail_ids=[mail_id])
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = base64.b64decode(b'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==')

        return response

    @http.route('/r/<string:code>/m/<int:stat_id>', type='http', auth="none")
    def full_url_redirect(self, code, stat_id, **post):
        # don't assume geoip is set, it is part of the website module
        # which mass_mailing doesn't depend on
        country_code = request.session.get('geoip', False) and request.session.geoip.get('country_code', False)

        request.env['link.tracker.click'].add_click(code, request.httprequest.remote_addr, country_code, stat_id=stat_id)
        return werkzeug.utils.redirect(request.env['link.tracker'].get_url_from_code(code), 301)

    @route('/mail/mailing/<int:mailing_id>/unsubscribe', type='http', website=True, auth='public')
    def mailing(self, mailing_id, email=None, res_id=None, token="", **post):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            if mailing.mailing_model_name == 'mail.mass_mailing.contact':
                contacts = request.env['mail.mass_mailing.contact'].sudo().search([('email', '=', email)])
                return request.render('mass_mailing.page_unsubscribe', {
                    'contacts': contacts,
                    'email': email,
                    'mailing_id': mailing_id})
            elif mailing.mailing_model_name == 'mail.mass_mailing.list':
                contact = request.env['mail.mass_mailing.contact'].sudo().search([('email', '=ilike', email)])
                opt_out_list_ids = contact.opt_out_list_ids.filtered(lambda rel: rel.opt_out == True).mapped('list_id')
                return request.render('mass_mailing.page_list_subscription', {
                    'email': email,
                    'mailing_id': mailing_id,
                    'list_ids': contact.list_ids,
                    'opt_out_list_ids': opt_out_list_ids,
                    'contact': contact
                })
            else:
                res_ids = [res_id and int(res_id)]
                right_token = mailing._unsubscribe_token(res_id, email)
                if not consteq(str(token), right_token):
                    raise exceptions.AccessDenied()
                mailing.update_opt_out(email, res_ids, True)
                return request.render('mass_mailing.page_unsubscribed', {
                    'email': email,
                    'mailing_id': mailing_id,
                    'res_id': res_id
                })

    @route('/mail/mailing/unsubscribe', type='json', auth='none')
    def unsubscribe(self, mailing_id, opt_in_ids, opt_out_ids, email):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            mailing.update_opt_out(email, opt_in_ids, False)
            mailing.update_opt_out(email, opt_out_ids, True)


    @route('/mail/mailing/subscribe_contact', type='json', auth='none')
    def subscribe_contact(self, email, mailing_id, res_id):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            res_id = res_id and int(res_id)
            res_ids = []

            if mailing.mailing_model_name == 'mail.mass_mailing.list':
                contacts = request.env['mail.mass_mailing.contact'].sudo().search([
                    ('email', '=', email),
                    ('list_ids', 'in', [mailing_list.id for mailing_list in mailing.contact_list_ids])
                ])
                res_ids = contacts.ids
            else:
                res_ids = [res_id]

            mailing.update_opt_out(email, res_ids, False)
            return 'success'
        return 'error'

    @route('/mail/mailing/feedback', type='json', auth='none')
    def send_feedback(self, mailing_id, email, feedback):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists() and email:
            model = request.env[mailing.mailing_model_real]
            email_field = 'email' if 'email' in model._fields else 'email_from'
            record = model.sudo().search([(email_field, '=ilike', email)])
            if record:
                record.sudo().message_post(body=_("Feedback from %s: %s" % (email, feedback)))
                return 'success'
            return 'not found'
        return 'error'

    @route('/mail/mailing/blacklist/check', type='json', auth='none')
    def check_blacklist(self, email):
        if email:
            record = request.env['mail.mass_mailing.blacklist'].sudo().search([('email', '=ilike', email)])
            if record.email:
                return 'found'
            return 'not found'
        return 'error'

    @route('/mail/mailing/blacklist/add', type='json', auth='none')
    def add_to_blacklist(self, email):
        if email:
            record = request.env['mail.mass_mailing.blacklist'].sudo().search([('email', '=ilike', email)])
            if not record.email:
                request.env['mail.mass_mailing.blacklist'].sudo().create({
                    'email': email,
                    'reason': "The recipient has added himself in the blacklist using the unsubscription page."
                })
                return 'success'
            return 'found'
        return 'error'

    @route('/mail/mailing/blacklist/remove', type='json', auth='none')
    def remove_from_blacklist(self, email):
        if email:
            record = request.env['mail.mass_mailing.blacklist'].sudo().search([('email', '=ilike', email)])
            if record.email:
                record.sudo().unlink()
                return 'success'
            return 'not found'
        return 'error'