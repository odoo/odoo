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


class test_portal(common.TransactionCase):

    def _mock_smtp_gateway(self, *args, **kwargs):
        return True

    def _mock_build_email(self, *args, **kwargs):
        self._build_email_args_list.append(args)
        self._build_email_kwargs_list.append(kwargs)
        return self.build_email_real(*args, **kwargs)

    def _init_mock_build_email(self):
        self._build_email_args_list = []
        self._build_email_kwargs_list = []

    def setUp(self):
        super(test_portal, self).setUp()
        self.ir_model = self.registry('ir.model')
        self.mail_group = self.registry('mail.group')
        self.mail_mail = self.registry('mail.mail')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Install mock SMTP gateway
        self._init_mock_build_email()
        self.build_email_real = self.registry('ir.mail_server').build_email
        self.registry('ir.mail_server').build_email = self._mock_build_email
        self.registry('ir.mail_server').send_email = self._mock_smtp_gateway

        # create a 'pigs' group that will be used through the various tests
        self.group_pigs_id = self.mail_group.create(self.cr, self.uid,
            {'name': 'Pigs', 'description': 'Fans of Pigs, unite !'})

    def test_00_mail_invite(self):
        cr, uid = self.cr, self.uid
        print 'cacaprout'
