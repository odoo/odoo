# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import common


class TestEventCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventCommon, cls).setUpClass()

        # User groups
        cls.group_employee_id = cls.env.ref('base.group_user').id
        cls.group_event_user_id = cls.env.ref('event.group_event_user').id
        cls.group_event_manager_id = cls.env.ref('event.group_event_manager').id
        cls.group_system_id = cls.env.ref('base.group_system').id

        # Test users to use through the various tests
        cls.user_eventuser = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Armande EventUser',
            'login': 'Armande',
            'email': 'armande.eventuser@example.com',
            'tz': 'Europe/Brussels',
            'groups_id': [(6, 0, [cls.group_employee_id, cls.group_event_user_id])]
        })
        cls.user_eventmanager = cls.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Bastien EventManager',
            'login': 'bastien',
            'email': 'bastien.eventmanager@example.com',
            'tz': 'Europe/Brussels',
            'groups_id': [(6, 0, [
                cls.group_employee_id,
                cls.group_event_manager_id,
                cls.group_system_id])]
        })

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'auto_confirm': True,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
        })

        # set country in order to format belgium numbers
        cls.event_0.company_id.write({'country_id': cls.env.ref('base.be').id})

    @classmethod
    def _create_registrations(cls, event, reg_count):
        # create some registrations
        registrations = cls.env['event.registration'].create([{
            'event_id': event.id,
            'name': 'Test Registration %s' % x,
            'email': '_test_reg_%s@example.com' % x,
            'phone': '04560000%s%s' % (x, x),
        } for x in range(0, reg_count)])
        return registrations
