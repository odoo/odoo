# -*- coding: utf-8 -*-

import werkzeug

from openerp import http, SUPERUSER_ID, _
from openerp.http import request


class MassMailController(http.Controller):

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', website=True, auth='public')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        if mailing.exists():
            res_ids = []
            if mailing.mailing_model == 'mail.mass_mailing.contact':
                contacts = request.env['mail.mass_mailing.contact'].sudo().search([
                    ('email', '=', email),
                    ('list_id', 'in', [mailing_list.id for mailing_list in mailing.contact_list_ids])
                ])
                res_ids = contacts.ids
            else:
                res_ids = [res_id]
            mailing.update_opt_out(mailing_id, email, res_ids, True)
            return _('You have been unsubscribed successfully')

    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='none')
    def track_mail_open(self, mail_id, **post):
        """ Email tracking. """
        mail_mail_stats = request.registry.get('mail.mail.statistics')
        mail_mail_stats.set_opened(request.cr, SUPERUSER_ID, mail_mail_ids=[mail_id])
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = 'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='.decode('base64')

        return response

    @http.route('/r/<string:code>/m/<int:stat_id>', type='http', auth="none")
    def full_url_redirect(self, code, stat_id, **post):
        cr, uid, context = request.cr, request.uid, request.context

        # don't assume geoip is set, it is part of the website module
        # which mass_mailing doesn't depend on
        country_code = request.session.get('geoip', False) and request.session.geoip.get('country_code', False)

        request.registry['link.tracker.click'].add_click(cr, uid, code, request.httprequest.remote_addr, country_code, stat_id=stat_id, context=context)
        return werkzeug.utils.redirect(request.registry['link.tracker'].get_url_from_code(cr, uid, code, context=context), 301)
