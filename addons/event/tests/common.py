# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from openerp import fields
from openerp.tests import common


class TestEventCommon(common.TransactionCase):

    def setUp(self):
        super(TestEventCommon, self).setUp()

        # Usefull models
        self.Users = self.env['res.users']
        self.Event = self.env['event.event']
        self.Registration = self.env['event.registration']
        self.EventMail = self.env['event.mail']

        # User groups
        self.group_employee_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_user')
        self.group_event_user_id = self.env['ir.model.data'].xmlid_to_res_id('event.group_event_user')
        self.group_event_manager_id = self.env['ir.model.data'].xmlid_to_res_id('event.group_event_manager')

        # Test users to use through the various tests
        self.user_eventuser = self.Users.with_context({'no_reset_password': True}).create({
            'name': 'Armande EventUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.eventuser@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_event_user_id])]
        })
        self.user_eventmanager = self.Users.with_context({'no_reset_password': True}).create({
            'name': 'Bastien EventManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.eventmanager@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_event_manager_id])]
        })
