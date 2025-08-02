# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests.common import new_test_user


class TestResPartner(TransactionCase):

    def test_meeting_count(self):
        test_user = new_test_user(self.env, login='test_user', groups='base.group_user, base.group_partner_manager')
        Partner = self.env['res.partner'].with_user(test_user)
        Event = self.env['calendar.event'].with_user(test_user)

        # Partner hierarchy
        #     1       5
        #    /|
        #   2 3
        #     |
        #     4

        test_partner_1 = Partner.create({'name': 'test_partner_1'})
        test_partner_2 = Partner.create({'name': 'test_partner_2', 'parent_id': test_partner_1.id})
        test_partner_3 = Partner.create({'name': 'test_partner_3', 'parent_id': test_partner_1.id})
        test_partner_4 = Partner.create({'name': 'test_partner_4', 'parent_id': test_partner_3.id})
        test_partner_5 = Partner.create({'name': 'test_partner_5'})
        test_partner_6 = Partner.create({'name': 'test_partner_6'})
        test_partner_7 = Partner.create({'name': 'test_partner_7', 'parent_id': test_partner_6.id})

        Event.create({'name': 'event_1',
                      'partner_ids': [(6, 0, [test_partner_1.id,
                                              test_partner_2.id,
                                              test_partner_3.id,
                                              test_partner_4.id])]})
        Event.create({'name': 'event_2',
                      'partner_ids': [(6, 0, [test_partner_1.id,
                                              test_partner_3.id])]})
        Event.create({'name': 'event_2',
                      'partner_ids': [(6, 0, [test_partner_2.id,
                                              test_partner_3.id])]})
        Event.create({'name': 'event_3',
                      'partner_ids': [(6, 0, [test_partner_3.id,
                                              test_partner_4.id])]})
        Event.create({'name': 'event_4',
                      'partner_ids': [(6, 0, [test_partner_1.id])]})
        Event.create({'name': 'event_5',
                      'partner_ids': [(6, 0, [test_partner_3.id])]})
        Event.create({'name': 'event_6',
                      'partner_ids': [(6, 0, [test_partner_4.id])]})
        Event.create({'name': 'event_7',
                      'partner_ids': [(6, 0, [test_partner_5.id])]})
        Event.create({'name': 'event_8',
                      'partner_ids': [(6, 0, [test_partner_5.id,
                                              test_partner_7.id])]})

        #Test rule to see if ir.rules are applied
        calendar_event_model_id = self.env['ir.model']._get('calendar.event').id
        self.env['ir.rule'].create({'name': 'test_rule',
                                    'model_id': calendar_event_model_id,
                                    'domain_force': [('name', 'not in', ['event_9', 'event_10'])],
                                    'perm_read': True,
                                    'perm_create': False,
                                    'perm_write': False})
        # create generally requires read -> prevented by above test rule
        Event.sudo().create({'name': 'event_9',
                      'partner_ids': [(6, 0, [test_partner_2.id,
                                              test_partner_3.id])]})

        Event.sudo().create({'name': 'event_10',
                      'partner_ids': [(6, 0, [test_partner_5.id])]})

        self.assertEqual(test_partner_1.meeting_count, 7)
        self.assertEqual(test_partner_2.meeting_count, 2)
        self.assertEqual(test_partner_3.meeting_count, 6)
        self.assertEqual(test_partner_4.meeting_count, 3)
        self.assertEqual(test_partner_5.meeting_count, 2)
        self.assertEqual(test_partner_6.meeting_count, 1)
        self.assertEqual(test_partner_7.meeting_count, 1)

    def test_meeting_count_access_error(self):
        main_co = self.env['res.company'].create({'name': 'main company'})
        be_co = self.env['res.company'].create({'name': 'belgian Company'})
        admin_user = self.env.ref('base.user_admin')
        admin_user.write({
            'company_id': main_co.id,
            'company_ids': [(4, main_co.id), (4, be_co.id)]
        })
        no_access_user = new_test_user(
            self.env,
            login='test_user',
            name="no access user",
            groups='base.group_user',
            company_id=main_co.id,
            company_ids=[main_co.id]
        )
        partner_be = be_co.partner_id
        partner_be.write({
            'company_id': be_co.id
        })
        access_user = new_test_user(
            self.env,
            login='test_user_2',
            name="laurie",
            groups='base.group_user',
            company_id=be_co.id,
            company_ids=[main_co.id, be_co.id],
        )
        laurie = access_user.commercial_partner_id
        laurie.write({
            'parent_id':  partner_be.id,
            'company_id': be_co.id,
        })
        self.env['calendar.event'].with_user(admin_user).create({
            'name':        'laurie Meeting',
            'partner_ids': [laurie.id],
        })
        self.env['calendar.event'].with_user(admin_user).create({
            'name': 'second meetin',
            'partner_ids': [laurie.id],
        })
        partner = self.env['res.partner'].with_user(no_access_user)
        meet_count = partner.search([('id', 'in', [laurie.id])]).mapped('meeting_count')
        self.assertEqual(meet_count, [2], 'the meeting count should me [2]')
