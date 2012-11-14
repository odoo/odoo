# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.tests import common


class TestMailMockups(common.TransactionCase):

    def _mock_smtp_gateway(self, *args, **kwargs):
        return True

    def _init_mock_build_email(self):
        self._build_email_args_list = []
        self._build_email_kwargs_list = []

    def _mock_build_email(self, *args, **kwargs):
        """ Mock build_email to be able to test its values. Store them into
            some internal variable for latter processing. """
        self._build_email_args_list.append(args)
        self._build_email_kwargs_list.append(kwargs)
        return self._build_email(*args, **kwargs)

    def setUp(self):
        super(TestMailMockups, self).setUp()
        # Install mock SMTP gateway
        self._init_mock_build_email()
        self._build_email = self.registry('ir.mail_server').build_email
        self.registry('ir.mail_server').build_email = self._mock_build_email
        self._send_email = self.registry('ir.mail_server').send_email
        self.registry('ir.mail_server').send_email = self._mock_smtp_gateway

    def tearDown(self):
        # Remove mocks
        self.registry('ir.mail_server').build_email = self._build_email
        self.registry('ir.mail_server').send_email = self._send_email
        super(TestMailMockups, self).tearDown()
