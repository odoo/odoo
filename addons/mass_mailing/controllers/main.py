
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request


class MassMailController(http.Controller):

    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='none')
    def track_mail_open(self, mail_id, **post):
        """ Email tracking. """
        mail_mail_stats = request.registry.get('mail.mail.statistics')
        mail_mail_stats.set_opened(request.cr, SUPERUSER_ID, mail_mail_ids=[mail_id])
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = 'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='.decode('base64')

        return response

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', auth='none', website=True)
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            if mailing.mailing_model == 'mail.mass_mailing.contact':
                contacts =request.env['mail.mass_mailing.contact'].sudo().search([('email', 'ilike', email)])
                return request.website.render('mass_mailing.page_unsubscribe', {'contacts': contacts, 'email': email, 'mailing_id':mailing_id})
            else:
                mailing.update_opt_out(mailing_id, email, [res_id], True)
                return request.website.render('mass_mailing.page_unsubscribed')

    @http.route(['/mail/mailing/unsubscribe'], type='json', auth='none', website=True)
    def unsubscribe(self, mailing_id, opt_in_ids, opt_out_ids, email):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            mailing.update_opt_out(mailing_id, email, opt_in_ids, False)
            mailing.update_opt_out(mailing_id, email, opt_out_ids, True) 

    @http.route('/website_mass_mailing/is_subscriber', type='json', auth="public", website=True)
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

    @http.route('/website_mass_mailing/subscribe', type='json', auth="public", website=True)
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

    @http.route('/r/<string:code>/m/<int:stat_id>', type='http', auth="none")
    def full_url_redirect(self, code, stat_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['website.links.click'].add_click(cr, uid, code, request.httprequest.remote_addr, request.session['geoip'].get('country_code'), stat_id=stat_id, context=context)
        return werkzeug.utils.redirect(request.registry['website.links'].get_url_from_code(cr, uid, code, context=context), 301)
