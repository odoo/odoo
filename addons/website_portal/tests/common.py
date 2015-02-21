# -*- coding: utf-8 -*-
from openerp.tests import common


class TestWebsitePortalCommon(common.TransactionCase):
    def setUp(self):
        super(TestWebsitePortalCommon, self).setUp()

        Users = self.env['res.users']

        group_portal_manager_id = self.ref('base.group_document_user')
        group_employee_id = self.ref('base.group_user')
        group_public_id = self.ref('base.group_public')

        self.user_employee = Users.with_context({'no_reset_password': True}).create({
            'name': 'Armande Employee',
            'login': 'armande',
            'alias_name': 'armande',
            'email': 'armande.employee@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [group_employee_id])]
        })
        self.user_portalmanager = Users.with_context({'no_reset_password': True}).create({
            'name': 'Bastien PortalManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.portalmanager@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [group_portal_manager_id, group_employee_id])]
        })
        self.user_public = Users.with_context({'no_reset_password': True}).create({
            'name': 'Cedric Public',
            'login': 'cedric',
            'alias_name': 'cedric',
            'email': 'cedric.public@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [group_public_id])]
        })
