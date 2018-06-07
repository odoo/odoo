# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route, request
from odoo.addons.mass_mailing.controllers.main import MassMailController
from odoo import _


class MassMailController(MassMailController):

    @route('/mail/mailing/<int:mailing_id>/unsubscribe', type='http', website=True, auth='public')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            if mailing.mailing_model_name == 'mail.mass_mailing.contact':
                contacts = request.env['mail.mass_mailing.contact'].sudo().search([('email', '=', email)])
                return request.render('website_mass_mailing.page_unsubscribe', {
                    'contacts': contacts,
                    'email': email,
                    'mailing_id': mailing_id})
            elif mailing.mailing_model_name == 'mail.mass_mailing.list':
                # Unique mailing list unsubscription
                # super(MassMailController, self).mailing(mailing_id, email=email, res_id=res_id, **post)
                # return request.render('website_mass_mailing.page_unsubscribed', {
                #     'email': email,
                #     'mailing_id': mailing_id,
                #     'res_id': res_id,
                #     'mailing_list_name': mailing.contact_list_ids[0].display_name
                # })

                # Choose your subscriptions
                contact = request.env['mail.mass_mailing.contact'].sudo().search([('email', '=ilike', email)])
                opt_out_list_ids = contact.opt_out_list_ids.filtered(lambda rel: rel.opt_out == True).mapped('list_id')
                return request.render('website_mass_mailing.page_list_subscription', {
                    'email': email,
                    'mailing_id': mailing_id,
                    'list_ids': contact.list_ids,
                    'opt_out_list_ids': opt_out_list_ids,
                    'contact': contact
                })
            else:
                super(MassMailController, self).mailing(mailing_id, email=email, res_id=res_id, **post)
                return request.render('website_mass_mailing.page_unsubscribed', {
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

    @route('/website_mass_mailing/is_subscriber', type='json', website=True, auth="public")
    def is_subscriber(self, list_id, **post):
        email = None
        if request.uid != request.website.user_id.id:
            email = request.env.user.email
        elif request.session.get('mass_mailing_email'):
            email = request.session['mass_mailing_email']

        is_subscriber = False
        if email:
            contacts_count = request.env['mail.mass_mailing.contact'].sudo().search_count([('list_ids', 'in', [int(list_id)]), ('email', '=', email), ('opt_out', '=', False)])
            is_subscriber = contacts_count > 0

        return {'is_subscriber': is_subscriber, 'email': email}

    @route('/website_mass_mailing/subscribe', type='json', website=True, auth="public")
    def subscribe(self, list_id, email, **post):
        Contacts = request.env['mail.mass_mailing.contact'].sudo()
        name, email = Contacts.get_name_email(email)

        contact_ids = Contacts.search([
            ('list_ids', 'in', [int(list_id)]),
            ('email', '=', email),
        ], limit=1)
        if not contact_ids:
            # inline add_to_list as we've already called half of it
            Contacts.create({'name': name, 'email': email, 'list_ids': [(6,0,[int(list_id)])]})
        elif contact_ids.opt_out:
            contact_ids.opt_out = False
        # add email to session
        request.session['mass_mailing_email'] = email
        return True

    @route(['/website_mass_mailing/get_content'], type='json', website=True, auth="public")
    def get_mass_mailing_content(self, newsletter_id, **post):
        data = self.is_subscriber(newsletter_id, **post)
        mass_mailing_list = request.env['mail.mass_mailing.list'].sudo().browse(int(newsletter_id))
        data['content'] = mass_mailing_list.popup_content,
        data['redirect_url'] = mass_mailing_list.popup_redirect_url
        return data
