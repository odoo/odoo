# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import HttpCase


class TestMassMailingControllers(MassMailCommon, HttpCase):

    def test_tracking_url_token(self):
        mail_mail = self.env['mail.mail'].create({})

        response = self.url_open(mail_mail._get_tracking_url())
        self.assertEqual(response.status_code, 200)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = werkzeug.urls.url_join(base_url, 'mail/track/%s/fake_token/blank.gif' % mail_mail.id)

        response = self.url_open(url)
        self.assertEqual(response.status_code, 400)
