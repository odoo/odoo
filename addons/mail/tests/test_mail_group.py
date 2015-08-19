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

from .common import TestMail
from openerp.exceptions import AccessError
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger


class TestMailGroup(TestMail):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_mail_group_access_rights(self):
        """ Testing mail_group access rights and basic mail_thread features """
        cr, uid, user_noone_id, user_employee_id = self.cr, self.uid, self.user_noone_id, self.user_employee_id

        # Do: Bert reads Jobs -> ok, public
        self.mail_group.read(cr, user_noone_id, [self.group_jobs_id])
        # Do: Bert read Pigs -> ko, restricted to employees
        with self.assertRaises(except_orm):
            self.mail_group.read(cr, user_noone_id, [self.group_pigs_id])
        # Do: Raoul read Pigs -> ok, belong to employees
        self.mail_group.read(cr, user_employee_id, [self.group_pigs_id])

        # Do: Bert creates a group -> ko, no access rights
        with self.assertRaises(AccessError):
            self.mail_group.create(cr, user_noone_id, {'name': 'Test'})
        # Do: Raoul creates a restricted group -> ok
        new_group_id = self.mail_group.create(cr, user_employee_id, {'name': 'Test'})
        # Do: Bert added in followers, read -> ok, in followers
        self.mail_group.message_subscribe_users(cr, uid, [new_group_id], [user_noone_id])
        self.mail_group.read(cr, user_noone_id, [new_group_id])

        # Do: Raoul reads Priv -> ko, private
        with self.assertRaises(except_orm):
            self.mail_group.read(cr, user_employee_id, [self.group_priv_id])
        # Do: Raoul added in follower, read -> ok, in followers
        self.mail_group.message_subscribe_users(cr, uid, [self.group_priv_id], [user_employee_id])
        self.mail_group.read(cr, user_employee_id, [self.group_priv_id])

        # Do: Raoul write on Jobs -> ok
        self.mail_group.write(cr, user_employee_id, [self.group_priv_id], {'name': 'modified'})
        # Do: Bert cannot write on Private -> ko (read but no write)
        with self.assertRaises(AccessError):
            self.mail_group.write(cr, user_noone_id, [self.group_priv_id], {'name': 're-modified'})
        # Test: Bert cannot unlink the group
        with self.assertRaises(except_orm):
            self.mail_group.unlink(cr, user_noone_id, [self.group_priv_id])
        # Do: Raoul unlinks the group, there are no followers and messages left
        self.mail_group.unlink(cr, user_employee_id, [self.group_priv_id])
        fol_ids = self.mail_followers.search(cr, uid, [('res_model', '=', 'mail.group'), ('res_id', '=', self.group_priv_id)])
        self.assertFalse(fol_ids, 'unlinked document should not have any followers left')
        msg_ids = self.mail_message.search(cr, uid, [('model', '=', 'mail.group'), ('res_id', '=', self.group_priv_id)])
        self.assertFalse(msg_ids, 'unlinked document should not have any followers left')
