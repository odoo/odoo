# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import urlparse
import werkzeug.urls

from odoo import api, fields, models, tools

from openerp.addons.link_tracker.models.link_tracker import URL_REGEX


class MailMail(models.Model):
    """Add the mass mailing campaign data to mail"""
    _inherit = ['mail.mail']

    mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    statistics_ids = fields.One2many('mail.mail.statistics', 'mail_mail_id', string='Statistics')

    @api.model
    def create(self, values):
        """ Override mail_mail creation to create an entry in mail.mail.statistics """
        # TDE note: should be after 'all values computed', to have values (FIXME after merging other branch holding create refactoring)
        mail = super(MailMail, self).create(values)
        if values.get('statistics_ids'):
            mail_sudo = mail.sudo()
            mail_sudo.statistics_ids.write({'message_id': mail_sudo.message_id, 'state': 'outgoing'})
        return mail

    def _get_tracking_url(self, partner=None):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        track_url = urlparse.urljoin(
            base_url, 'mail/track/%(mail_id)s/blank.gif?%(params)s' % {
                'mail_id': self.id,
                'params': werkzeug.url_encode({'db': self.env.cr.dbname})
            }
        )
        return '<img src="%s" alt=""/>' % track_url

    def _get_unsubscribe_url(self, email_to):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': self.mailing_id.id,
                'params': werkzeug.url_encode({'db': self.env.cr.dbname, 'res_id': self.res_id, 'email': email_to})
            }
        )
        return url

    @api.multi
    def send_get_mail_body(self, partner=None):
        """ Override to add the tracking URL to the body and to add
        Statistic_id in shorted urls """
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        self.ensure_one()
        body = super(MailMail, self).send_get_mail_body(partner=partner)

        if self.mailing_id and body and self.statistics_ids:
            for match in re.findall(URL_REGEX, self.body_html):
                href = match[0]
                url = match[1]

                parsed = urlparse.urlparse(url, scheme='http')

                if parsed.scheme.startswith('http') and parsed.path.startswith('/r/'):
                    new_href = href.replace(url, url + '/m/' + str(self.statistics_ids[0].id))
                    body = body.replace(href, new_href)

        # prepend <base> tag for images using absolute urls
        domain = self.env["ir.config_parameter"].get_param("web.base.url")
        base = "<base href='%s'>" % domain
        body = tools.append_content_to_html(base, body, plaintext=False, container_tag='div')
        # resolve relative image url to absolute for outlook.com
        def _sub_relative2absolute(match):
            return match.group(1) + urlparse.urljoin(domain, match.group(2))
        body = re.sub('(<img(?=\s)[^>]*\ssrc=")(/[^/][^"]+)', _sub_relative2absolute, body)
        body = re.sub(r'(<[^>]+\bstyle="[^"]+\burl\(\'?)(/[^/\'][^\'")]+)', _sub_relative2absolute, body)

        # generate tracking URL
        if self.statistics_ids:
            tracking_url = self._get_tracking_url(partner)
            if tracking_url:
                body = tools.append_content_to_html(body, tracking_url, plaintext=False, container_tag='div')
        return body

    @api.multi
    def send_get_email_dict(self, partner=None):
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        res = super(MailMail, self).send_get_email_dict(partner)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if self.mailing_id and res.get('body') and res.get('email_to'):
            emails = tools.email_split(res.get('email_to')[0])
            email_to = emails and emails[0] or False
            unsubscribe_url = self._get_unsubscribe_url(email_to)
            link_to_replace = base_url + '/unsubscribe_from_list'
            if link_to_replace in res['body']:
                res['body'] = res['body'].replace(link_to_replace, unsubscribe_url if unsubscribe_url else '#')
        return res

    @api.multi
    def _postprocess_sent_message(self, mail_sent=True):
        for mail in self:
            if mail_sent is True and mail.statistics_ids:
                mail.statistics_ids.write({'sent': fields.Datetime.now(), 'exception': False})
            elif mail_sent is False and mail.statistics_ids:
                mail.statistics_ids.write({'exception': fields.Datetime.now()})
        return super(MailMail, self)._postprocess_sent_message(mail_sent=mail_sent)
