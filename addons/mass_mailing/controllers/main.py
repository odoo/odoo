
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

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', auth='none')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        MassMailing = request.registry['mail.mass_mailing']
        mailing_ids = MassMailing.exists(cr, SUPERUSER_ID, [mailing_id], context=context)
        if not mailing_ids:
            return 'KO'
        mailing = MassMailing.browse(cr, SUPERUSER_ID, mailing_ids[0], context=context)
        if mailing.mailing_model == 'mail.mass_mailing.contact':
            list_ids = [l.id for l in mailing.contact_list_ids]
            record_ids = request.registry[mailing.mailing_model].search(cr, SUPERUSER_ID, [('list_id', 'in', list_ids), ('id', '=', res_id), ('email', 'ilike', email)], context=context)
            request.registry[mailing.mailing_model].write(cr, SUPERUSER_ID, record_ids, {'opt_out': True}, context=context)
        else:
            email_fname = None
            model = request.registry[mailing.mailing_model]
            if 'email_from' in model._fields:
                email_fname = 'email_from'
            elif 'email' in model._fields:
                email_fname = 'email'
            if email_fname:
                record_ids = model.search(cr, SUPERUSER_ID, [('id', '=', res_id), (email_fname, 'ilike', email)], context=context)
            if 'opt_out' in model._fields:
                model.write(cr, SUPERUSER_ID, record_ids, {'opt_out': True}, context=context)
        return 'OK'

    @http.route(['/website_mass_mailing/is_subscriber'], type='json', auth="public", website=True)
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

    @http.route(['/website_mass_mailing/subscribe'], type='json', auth="public", website=True)
    def subscribe(self, list_id, email, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Contacts = request.registry['mail.mass_mailing.contact']
        parsed_email = Contacts.get_name_email(email, context=context)[1]

        contact_ids = Contacts.search_read(
            cr, SUPERUSER_ID,
            [('list_id', '=', int(list_id)), ('email', '=', parsed_email)],
            ['opt_out'], context=context)
        if not contact_ids:
            Contacts.add_to_list(cr, SUPERUSER_ID, email, int(list_id), context=context)
        else:
            if contact_ids[0]['opt_out']:
                Contacts.write(cr, SUPERUSER_ID, [contact_ids[0]['id']], {'opt_out': False}, context=context)
        # add email to session
        request.session['mass_mailing_email'] = email
        return True
