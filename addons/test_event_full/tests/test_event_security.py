# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.event.tests.common import TestEventCommon
from odoo.exceptions import AccessError
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestEventSecurity(TestEventCommon):

    @users('user_employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_model')
    def test_event_access_employee(self):
        # Event: read ok
        event = self.event_0.with_user(self.env.user)
        event.read(['name'])

        # Event: read only
        with self.assertRaises(AccessError):
            self.env['event.event'].create({
                'name': 'TestEvent',
                'date_begin': datetime.now() + relativedelta(days=-1),
                'date_end': datetime.now() + relativedelta(days=1),
                'seats_limited': True,
                'seats_max': 10,
            })
        with self.assertRaises(AccessError):
            event.write({
                'name': 'TestEvent Modified',
            })

        # Event Type
        with self.assertRaises(AccessError):
            self.event_type_complex.with_user(self.env.user).read(['name'])
        with self.assertRaises(AccessError):
            self.event_type_complex.with_user(self.env.user).write({'name': 'Test Write'})

        # Event Stage
        with self.assertRaises(AccessError):
            self.env['event.stage'].create({
                'name': 'TestStage',
            })

        # Event Registration
        with self.assertRaises(AccessError):
            self.env['event.registration'].search([])

    @users('user_eventregistrationdesk')
    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_model')
    def test_event_access_event_registration(self):
        # Event: read ok
        event = self.event_0.with_user(self.env.user)
        event.read(['name', 'user_id', 'kanban_state_label'])

        # Event: read only
        with self.assertRaises(AccessError):
            event.name = 'Test'
        with self.assertRaises(AccessError):
            event.unlink()

        # Event Registration
        registration = self.env['event.registration'].create({
            'event_id': self.event_0.id,
        })
        self.assertEqual(registration.event_id.name, self.event_0.name, 'Registration users should be able to read')
        registration.name = 'Test write'
        with self.assertRaises(AccessError):
            registration.unlink()

    @users('user_eventuser')
    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_model')
    def test_event_access_event_user(self):
        # Event
        event = self.event_0.with_user(self.env.user)
        event.read(['name', 'user_id', 'kanban_state_label'])
        event.write({'name': 'New name'})
        self.env['event.event'].create({
            'name': 'Event',
            'date_begin': datetime.now() + relativedelta(days=-1),
            'date_end': datetime.now() + relativedelta(days=1),
        })

        # Event: cannot unlink
        with self.assertRaises(AccessError):
            event.unlink()

        # Event Type
        with self.assertRaises(AccessError):
            self.env['event.type'].create({
                'name': 'ManagerEventType',
                'event_type_mail_ids': [(5, 0), (0, 0, {
                    'interval_nbr': 1, 'interval_unit': 'days', 'interval_type': 'before_event',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')})]
            })

    @users('user_eventmanager')
    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_model')
    def test_event_access_event_manager(self):
        # Event Type
        event_type = self.env['event.type'].create({
            'name': 'ManagerEventType',
            'event_type_mail_ids': [(5, 0), (0, 0, {
                'interval_nbr': 1, 'interval_unit': 'days', 'interval_type': 'before_event',
                'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')})]
        })
        event_type.write({'name': 'New Name'})

        # Event
        event = self.env['event.event'].create({
            'name': 'ManagerEvent',
            'date_begin': datetime.now() + relativedelta(days=-1),
            'date_end': datetime.now() + relativedelta(days=1),
        })
        event.write({'name': 'New Event Name'})

        # Event Stage
        stage = self.env['event.stage'].create({'name': 'test'})
        stage.write({'name': 'ManagerTest'})
        event.write({'stage_id': stage.id})

        # Event Registration
        registration = self.env['event.registration'].create({'event_id': event.id, 'name': 'Myself'})
        registration.write({'name': 'Myself2'})
        registration.unlink()

        event.unlink()
        stage.unlink()
        event_type.unlink()

        # Settings access rights required to enable some features
        self.user_eventmanager.write({'groups_id': [
            (3, self.env.ref('base.group_system').id),
            (4, self.env.ref('base.group_erp_manager').id)
        ]})
        with self.assertRaises(AccessError):
            event_config = self.env['res.config.settings'].with_user(self.user_eventmanager).create({
            })
            event_config.execute()

    def test_implied_groups(self):
        """Test that the implied groups are correctly set.

        - Event Manager imply Event User
        - Event User imply Registration user
        """
        # Event Manager
        self.assertTrue(
            self.user_eventmanager.has_group('event.group_event_user'),
            'The event manager group must imply the event user group')
        self.assertTrue(
            self.user_eventmanager.has_group('event.group_event_registration_desk'),
            'The event manager group must imply the registration user group')

        # Event User
        self.assertTrue(
            self.user_eventuser.has_group('event.group_event_registration_desk'),
            'The event user group must imply the event user group')
        self.assertFalse(
            self.user_eventuser.has_group('event.group_event_manager'),
            'The event user group must not imply the event user group')

        # Registration User
        self.assertFalse(
            self.user_eventregistrationdesk.has_group('event.group_event_manager'),
            'The event registration group must not imply the event user manager')
        self.assertFalse(
            self.user_eventregistrationdesk.has_group('event.group_event_user'),
            'The event registration group must not imply the event user group')

    def test_multi_companies(self):
        """Test ACLs with multi company. """
        company_1 = self.env.ref("base.main_company")
        company_2 = self.env['res.company'].create({'name': 'Company 2'})
        user_company_1 = self.user_eventuser

        event_company_1, event_company_2 = self.env['event.event'].create([
            {
                'name': 'Event Company 1',
                'date_begin': datetime.now() + relativedelta(days=-1),
                'date_end': datetime.now() + relativedelta(days=1),
                'company_id': company_1.id,
            }, {
                'name': 'Event Company 2',
                'date_begin': datetime.now() + relativedelta(days=-1),
                'date_end': datetime.now() + relativedelta(days=1),
                'company_id': company_2.id,
            }
        ])

        registration_company_1, registration_company_2 = self.env['event.registration'].create([
            {
                'name': 'Registration Company 1',
                'event_id': event_company_1.id,
                'company_id': company_1.id,
            }, {
                'name': 'Registration Company 2',
                'event_id': event_company_2.id,
                'company_id': company_2.id,
            }
        ])

        result = self.env['event.event'].with_user(user_company_1).search([])
        self.assertIn(event_company_1, result, 'You must be able to read the events in your company')
        self.assertNotIn(event_company_2, result, 'You must not be able to read events outside of your company')

        result = self.env['event.registration'].with_user(user_company_1).search([])
        self.assertIn(registration_company_1, result, 'You must be able to read the registrations in your company')
        self.assertNotIn(registration_company_2, result, 'You must not be able to read registrations outside of your company')
