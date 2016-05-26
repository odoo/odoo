# -*- coding: utf-8 -*-

from openerp import http, SUPERUSER_ID
from openerp.addons.mass_mailing.controllers.main import MassMailController
from openerp.http import request


class MassMailController(MassMailController):

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', website=True, auth='public')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            if mailing.mailing_model == 'mail.mass_mailing.contact':
                contacts = request.env['mail.mass_mailing.contact'].sudo().search([('email', '=', email)])
                return request.website.render('website_mass_mailing.page_unsubscribe', {
                    'contacts': contacts,
                    'email': email,
                    'mailing_id': mailing_id})
            else:
                super(MassMailController, self).mailing(mailing_id, email=email, res_id=res_id, **post)
                return request.website.render('website_mass_mailing.page_unsubscribed')

    @http.route(['/mail/mailing/unsubscribe'], type='json', auth='none')
    def unsubscribe(self, mailing_id, opt_in_ids, opt_out_ids, email):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            mailing.update_opt_out(mailing_id, email, opt_in_ids, False)
            mailing.update_opt_out(mailing_id, email, opt_out_ids, True)

    @http.route('/website_mass_mailing/is_subscriber', type='json', website=True, auth="public")
    def is_subscriber(self, list_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Contacts = request.registry['mail.mass_mailing.contact']
        Users = request.registry['res.users']

        is_subscriber = False
        email = None
        if uid != request.website.user_id.id:
            email = Users.browse(cr, SUPERUSER_ID, uid, context).email
        elif request.session.get('mass_mailing_email'):
            email = request.session['mass_mailing_email']

        if email:
            contact_ids = Contacts.search(cr, SUPERUSER_ID, [('list_id', '=', int(list_id)), ('email', '=', email), ('opt_out', '=', False)], context=context)
            is_subscriber = len(contact_ids) > 0

        return {'is_subscriber': is_subscriber, 'email': email}

    @http.route('/website_mass_mailing/subscribe', type='json', website=True, auth="public")
    def subscribe(self, list_id, email, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Contacts = request.registry['mail.mass_mailing.contact']

        contact_ids = Contacts.search_read(cr, SUPERUSER_ID, [('list_id', '=', int(list_id)), ('email', '=', email)], ['opt_out'], context=context)
        if not contact_ids:
            Contacts.add_to_list(cr, SUPERUSER_ID, email, int(list_id), context=context)
        else:
            if contact_ids[0]['opt_out']:
                Contacts.write(cr, SUPERUSER_ID, [contact_ids[0]['id']], {'opt_out': False}, context=context)
        # add email to session
        request.session['mass_mailing_email'] = email
        return True

    @http.route(['/website_mass_mailing/get_content'], type='json', website=True, auth="public")
    def get_mass_mailing_content(self, newsletter_id, **post):
        data = self.is_subscriber(newsletter_id, **post)
        mass_mailing_list = request.registry['mail.mass_mailing.list'].browse(request.cr, SUPERUSER_ID, int(newsletter_id), request.context)
        data.update({
            'content': mass_mailing_list.popup_content,
            'redirect_url': mass_mailing_list.popup_redirect_url
            })
        return data
