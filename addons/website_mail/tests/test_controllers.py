# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.mail.tests.common import TestMail
from openerp.addons.website_mail.controllers.main import WebsiteMail
from openerp.tools import mute_logger, email_split


class TestControllers(TestMail):

    def test_00_subscribe(self):
        # from openerp.addons.web.http import request
        # print request

        cr, uid = self.cr, self.uid
        # context = { }
        # email = 'Marcel Dupuis <marcel.dupuis@example.com>'
        # website_mail = WebsiteMail()

        # pid = website_mail._find_or_create_partner(email, context)
        # partner = self.res_partner.browse(cr, uid, pid)
        # print partner.name, partner.email
