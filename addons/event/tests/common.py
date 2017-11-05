# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import common


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
        group_system = self.env.ref('base.group_system')

        # Test users to use through the various tests
        self.user_eventuser = self.Users.with_context({'no_reset_password': True}).create({
            'name': 'Armande EventUser',
            'login': 'Armande',
            'email': 'armande.eventuser@example.com',
            'tz': 'Europe/Brussels',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_event_user_id])]
        })
        self.user_eventmanager = self.Users.with_context({'no_reset_password': True}).create({
            'name': 'Bastien EventManager',
            'login': 'bastien',
            'email': 'bastien.eventmanager@example.com',
            'tz': 'Europe/Brussels',
            'groups_id': [(6, 0, [
                self.group_employee_id,
                self.group_event_manager_id,
                group_system.id])]
        })

        self.event_0 = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'registration_ids': [(0, 0, {
                'partner_id': self.user_eventuser.partner_id.id,
            })]
        })
