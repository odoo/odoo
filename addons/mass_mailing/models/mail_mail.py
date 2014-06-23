# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import urllib
import urlparse

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields


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
            mail = self.browse(cr, SUPERUSER_ID, mail_id)
            for stat in mail.statistics_ids:
                self.pool['mail.mail.statistics'].write(cr, uid, [stat.id], {'message_id': mail.message_id}, context=context)
        return mail_id

    def _get_tracking_url(self, cr, uid, mail, partner=None, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        track_url = urlparse.urljoin(
            base_url, 'mail/track/%(mail_id)s/blank.gif?%(params)s' % {
                'mail_id': mail.id,
                'params': urllib.urlencode({'db': cr.dbname})
            }
        )
        return '<img src="%s" alt=""/>' % track_url

    def _get_unsubscribe_url(self, cr, uid, mail, email_to, msg=None, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': mail.mailing_id.id,
                'params': urllib.urlencode({'db': cr.dbname, 'res_id': mail.res_id, 'email': email_to})
            }
        )
        return '<small><a href="%s">%s</a></small>' % (url, msg or 'Click to unsubscribe')

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """ Override to add the tracking URL to the body. """
        body = super(MailMail, self).send_get_mail_body(cr, uid, mail, partner=partner, context=context)

        # generate tracking URL
        if mail.statistics_ids:
            tracking_url = self._get_tracking_url(cr, uid, mail, partner, context=context)
            if tracking_url:
                body = tools.append_content_to_html(body, tracking_url, plaintext=False, container_tag='div')
        return body

    def send_get_email_dict(self, cr, uid, mail, partner=None, context=None):
        res = super(MailMail, self).send_get_email_dict(cr, uid, mail, partner, context=context)
        if mail.mailing_id and res.get('body') and res.get('email_to'):
            emails = tools.email_split(res.get('email_to')[0])
            email_to = emails and emails[0] or False
            unsubscribe_url = self._get_unsubscribe_url(cr, uid, mail, email_to, context=context)
            if unsubscribe_url:
                res['body'] = tools.append_content_to_html(res['body'], unsubscribe_url, plaintext=False, container_tag='p')
        return res

    def _postprocess_sent_message(self, cr, uid, mail, context=None, mail_sent=True):
        if mail_sent is True and mail.statistics_ids:
            self.pool['mail.mail.statistics'].write(cr, uid, [s.id for s in mail.statistics_ids], {'sent': fields.datetime.now()}, context=context)
        elif mail_sent is False and mail.statistics_ids:
            self.pool['mail.mail.statistics'].write(cr, uid, [s.id for s in mail.statistics_ids], {'exception': fields.datetime.now()}, context=context)
        return super(MailMail, self)._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=mail_sent)
