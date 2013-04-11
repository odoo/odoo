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

from openerp.osv.orm import except_orm
from openerp.tests import common
from openerp.tools import mute_logger


class TestPortalProject(common.TransactionCase):

    def setUp(self):
        super(TestPortalProject, self).setUp()
        cr, uid = self.cr, self.uid

        # Useful models
        self.project_project = self.registry('project.project')
        self.project_task = self.registry('project.task')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        self.group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Find Project User group
        group_project_user_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'project', 'group_project_user')
        self.group_project_user_id = group_project_user_ref and group_project_user_ref[1] or False

        # Find Portal group
        group_portal_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_portal')
        self.group_portal_id = group_portal_ref and group_portal_ref[1] or False

        # Find Anonymous group
        group_anonymous_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_anonymous')
        self.group_anonymous_id = group_anonymous_ref and group_anonymous_ref[1] or False

        # Test users to use through the various tests
        self.user_alfred_id = self.res_users.create(cr, uid, {
                        'name': 'Alfred Employee',
                        'login': 'alfred',
                        'alias_name': 'alfred',
                        'groups_id': [(6, 0, [self.group_employee_id, self.group_project_user_id])]
                    })
        self.user_bert_id = self.res_users.create(cr, uid, {
                        'name': 'Bert Nobody',
                        'login': 'bert',
                        'alias_name': 'bert',
                        'groups_id': [(6, 0, [])]
                    })
        self.user_chell_id = self.res_users.create(cr, uid, {
                        'name': 'Chell Portal',
                        'login': 'chell',
                        'alias_name': 'chell',
                        'groups_id': [(6, 0, [self.group_portal_id])]
                    })
        self.user_donovan_id = self.res_users.create(cr, uid, {
                        'name': 'Donovan Anonymous',
                        'login': 'donovan',
                        'alias_name': 'donovan',
                        'groups_id': [(6, 0, [self.group_anonymous_id])]
                    })

        # Test 'Pigs' project to use through the various tests
        self.project_pigs_id = self.project_project.create(cr, uid,
            {'name': 'Pigs', 'alias_contact': 'everyone', 'visibility': 'public'},
            {'mail_create_nolog': True})

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    def test_00_project_access_rights(self):
        """ Test basic project access rights, for project and portal_project """
        cr, uid, pigs_id = self.cr, self.uid, self.project_pigs_id

        # ----------------------------------------
        # CASE1: public project
        # ----------------------------------------

        # Do: Alfred read project -> ok (employee ok public)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])

        # Do: Bert read project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])

        # Do: Chell read project -> ok (portal ok public)
        self.project_project.read(cr, self.user_chell_id, pigs_id, ['name'])

        # Do: Alfred read project -> ok (anonymous ok public)
        self.project_project.read(cr, self.user_donovan_id, pigs_id, ['name'])

        # ----------------------------------------
        # CASE2: portal project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'visibility': 'portal'})

        # Do: Alfred read project -> ok (employee ok public)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])

        # Do: Bert read project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])

        # Do: Chell read project -> ok (portal ok public)
        self.project_project.read(cr, self.user_chell_id, pigs_id, ['name'])

        # Do: Alfred read project -> ko (anonymous ko portal)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])

        # ----------------------------------------
        # CASE3: employee project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'visibility': 'employees'})

        # Do: Alfred read project -> ok (employee ok employee)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])

        # Do: Bert read project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])

        # Do: Chell read project -> ko (portal ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_chell_id, pigs_id, ['name'])

        # Do: Alfred read project -> ko (anonymous ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])

        # ----------------------------------------
        # CASE4: followers project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'visibility': 'followers'})

        # Do: Alfred read project -> ko (employee ko followers)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_alfred_id, pigs_id, ['name'])

        # Do: Bert read project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])

        # Do: Chell read project -> ko (portal ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_chell_id, pigs_id, ['name'])

        # Do: Alfred read project -> ko (anonymous ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])
