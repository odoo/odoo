# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import urlparse
import re
import werkzeug.urls

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields


URL_REGEX = r'(\bhref=[\'"]([^\'"]+)[\'"])'


class MailMail(osv.Model):
    """Add the mass mailing campaign data to mail"""
    _name = 'mail.mail'
    _inherit = ['mail.mail']

    _columns = {
        'mailing_id': fields.many2one('mail.mass_mailing', 'Mass Mailing'),
        'statistics_ids': fields.one2many(
            'mail.mail.statistics', 'mail_mail_id',
            string='Statistics',
        ),
    }

    def create(self, cr, uid, values, context=None):
        """ Override mail_mail creation to create an entry in mail.mail.statistics """
        # TDE note: should be after 'all values computed', to have values (FIXME after merging other branch holding create refactoring)
        mail_id = super(MailMail, self).create(cr, uid, values, context=context)
        if values.get('statistics_ids'):
            mail = self.browse(cr, SUPERUSER_ID, mail_id, context=context)
            for stat in mail.statistics_ids:
                self.pool['mail.mail.statistics'].write(cr, uid, [stat.id], {'message_id': mail.message_id, 'state': 'outgoing'}, context=context)
        return mail_id

    def _get_tracking_url(self, cr, uid, mail, partner=None, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        track_url = urlparse.urljoin(
            base_url, 'mail/track/%(mail_id)s/blank.gif?%(params)s' % {
                'mail_id': mail.id,
                'params': werkzeug.url_encode({'db': cr.dbname})
            }
        )
        return '<img src="%s" alt=""/>' % track_url

    def _get_unsubscribe_url(self, cr, uid, mail, email_to, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': mail.mailing_id.id,
                'params': werkzeug.url_encode({'db': cr.dbname, 'res_id': mail.res_id, 'email': email_to})
            }
        )
        return url

    def send_get_mail_body(self, cr, uid, ids, partner=None, context=None):
        """ Override to add the tracking URL to the body and to add
        Statistic_id in shorted urls """
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        body = super(MailMail, self).send_get_mail_body(cr, uid, ids, partner=partner, context=context)
        mail = self.browse(cr, uid, ids[0], context=context)

        links_blacklist = ['/unsubscribe_from_list']

        if mail.mailing_id and body and mail.statistics_ids:
            for match in re.findall(URL_REGEX, mail.body_html):

                href = match[0]
                url = match[1]

                if not [s for s in links_blacklist if s in href]:
                    new_href = href.replace(url, url + '/m/' + str(mail.statistics_ids[0].id))
                    body = body.replace(href, new_href)

        # prepend <base> tag for images using absolute urls
        domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.base.url", context=context)
        base = "<base href='%s'>" % domain
        body = tools.append_content_to_html(base, body, plaintext=False, container_tag='div')
        # resolve relative image url to absolute for outlook.com
        def _sub_relative2absolute(match):
            return match.group(1) + urlparse.urljoin(domain, match.group(2))
        body = re.sub('(<img(?=\s)[^>]*\ssrc=")(/[^/][^"]+)', _sub_relative2absolute, body)
        body = re.sub(r'(<[^>]+\bstyle="[^"]+\burl\(\'?)(/[^/\'][^\'")]+)', _sub_relative2absolute, body)

        # generate tracking URL
        if mail.statistics_ids:
            tracking_url = self._get_tracking_url(cr, uid, mail, partner, context=context)
            if tracking_url:
                body = tools.append_content_to_html(body, tracking_url, plaintext=False, container_tag='div')
        return body

    def send_get_email_dict(self, cr, uid, ids, partner=None, context=None):
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        res = super(MailMail, self).send_get_email_dict(cr, uid, ids, partner, context=context)
        mail = self.browse(cr, uid, ids[0], context=context)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        if mail.mailing_id and res.get('body') and res.get('email_to'):
            emails = tools.email_split(res.get('email_to')[0])
            email_to = emails and emails[0] or False
            unsubscribe_url= self._get_unsubscribe_url(cr, uid, mail, email_to, context=context)
            link_to_replace =  base_url+'/unsubscribe_from_list'
            if link_to_replace in res['body']:
                res['body'] = res['body'].replace(link_to_replace, unsubscribe_url if unsubscribe_url else '#')
        return res

    def _postprocess_sent_message(self, cr, uid, mail, context=None, mail_sent=True):
        if mail_sent is True and mail.statistics_ids:
            self.pool['mail.mail.statistics'].write(cr, uid, [s.id for s in mail.statistics_ids], {'sent': fields.datetime.now(), 'exception': False}, context=context)
        elif mail_sent is False and mail.statistics_ids:
            self.pool['mail.mail.statistics'].write(cr, uid, [s.id for s in mail.statistics_ids], {'exception': fields.datetime.now()}, context=context)
        return super(MailMail, self)._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=mail_sent)
