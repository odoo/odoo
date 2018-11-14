# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug import urls

from odoo.addons.test_mass_mailing.tests.common import MassMailingCase
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMassMail(MassMailingCase):

    def setUp(self):
        """ In this setup we prepare 20 blacklist entries. We therefore add
        20 recipients compared to first test in order to have comparable results. """
        super(TestMassMail, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 6)]
        self.mm_recs = self.env['mass.mail.test.bl'].create(values)

        self.env['mail.blacklist'].create({
            'email': 'rec.2@example.com'
        })

        self.test_medium = self.env['utm.medium'].create({'name': 'TestMedium'})

    @users('marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_link_tracker(self):
        _url = 'https://www.example.com/foo/bar?baz=qux'
        mailing = self.env['mail.mass_mailing'].create({
            'name': 'TestMailing',
            'medium_id': self.test_medium.id,
            'body_html': '<p>Hello <a role="button" href="%s">${object.name}</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>' % _url,
            'reply_to_mode': 'email',
            'mailing_model_id': self.ref('test_mass_mailing.model_mass_mail_test_bl'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        mailing.send_mail()

        # basic test emails are sent
        self.assertEqual(mailing.sent, 5)
        self.assertEqual(mailing.delivered, 5)

        # link trackers
        links = self.env['link.tracker'].sudo().search([('mass_mailing_id', '=', mailing.id)])
        self.assertEqual(len(links), 1)
        self.assertEqual(links.mapped('url'), [_url])
        # check UTMS are correctly set on redirect URL
        redirect_url = urls.url_parse(links.redirected_url)
        redirect_params = redirect_url.decode_query().to_dict(flat=True)
        self.assertEqual(redirect_url.scheme, 'https')
        self.assertEqual(redirect_url.decode_netloc(), 'www.example.com')
        self.assertEqual(redirect_url.path, '/foo/bar')
        self.assertEqual(redirect_params, {
            'utm_source': mailing.name,
            'utm_medium': self.test_medium.name,
            'baz': 'qux',
        })
