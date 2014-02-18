# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
