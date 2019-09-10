# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://openerp.com>
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

class TestNote(common.TransactionCase):

    def test_bug_lp_1156215(self):
        """ensure any users can create new users"""
        cr, uid = self.cr, self.uid
        IMD = self.registry('ir.model.data')
        Users = self.registry('res.users')

        _, demo_user = IMD.get_object_reference(cr, uid, 'base', 'user_demo')
        _, group_id = IMD.get_object_reference(cr, uid, 'base', 'group_erp_manager')

        Users.write(cr, uid, [demo_user], {
            'groups_id': [(4, group_id)],
        })

        # must not fail
        Users.create(cr, demo_user, {
            'name': 'test bug lp:1156215',
            'login': 'lp_1156215',
        })
