# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import users
from odoo.tools import mute_logger


class TestMailingABTesting(MassMailCommon):

    def _create_ab_testing_mailings(self, nbr_testing_mailings, testing_mode='based_on'):
        mailing_list = self._create_mailing_list_of_x_contacts(150)
        ab_testing = self.env['mailing.ab.testing'].create({
            'name': 'A/B Testing',
            'contact_list_ids': mailing_list.ids,
            'sample_size': '25',
            'testing_mode': testing_mode,  # can be "based_on" or "manual"
        })
        vals_list = []
        for i in range(nbr_testing_mailings):
            values = dict({
                'testing_mailing_id': ab_testing.id,
                'mailing_model_id': ab_testing.mailing_model_id.id,
                'mailing_domain': ab_testing.mailing_domain,
                'contact_list_ids': ab_testing.contact_list_ids.ids,
                'mailing_type': ab_testing.mailing_type,
            })
            version_id = self.env['mailing.mailing.version']._search_create_version_id(chr(ord('A') + i)).id
            values.update({
                'subject': 'Test %s' % (i + 1),
                'version_id': version_id,
            })
            vals_list.append(values)
        self.env['mailing.mailing'].create(vals_list)
        ab_testing.mailing_ids.invalidate_cache()
        return ab_testing

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_ab_testing_auto_flow(self):
        ab_testing = self._create_ab_testing_mailings(2)
        mailing_a = ab_testing.mailing_ids[0]
        mailing_b = ab_testing.mailing_ids[1]
        self.assertEqual(ab_testing.state, 'new')

        self.assertEqual(len(ab_testing.mailing_ids), 2)
        self.assertEqual(ab_testing.mailing_ids[0].contact_ab_pc, 0.125)
        self.assertEqual(ab_testing.mailing_ids[1].contact_ab_pc, 0.125)

        with self.mock_mail_gateway():
            ab_testing.action_send_mailings()
        self.assertEqual(ab_testing.state, 'in_progress')
        self.assertEqual(mailing_a.state, 'done')
        self.assertEqual(mailing_b.state, 'done')
        self.assertEqual(mailing_a.opened_ratio, 0)
        self.assertEqual(mailing_b.opened_ratio, 0)

        total_traces = mailing_a.mailing_trace_ids + mailing_b.mailing_trace_ids
        unique_recipients_used = set(map(lambda mail: mail.res_id, total_traces.mail_mail_id))
        self.assertEqual(len(mailing_a.mailing_trace_ids), 18)
        self.assertEqual(len(mailing_b.mailing_trace_ids), 18)
        self.assertEqual(len(unique_recipients_used), 36)

        mailing_a.mailing_trace_ids[:9].set_opened()
        mailing_b.mailing_trace_ids[:3].set_opened()
        ab_testing.mailing_ids.invalidate_cache()

        self.assertEqual(mailing_a.opened_ratio, 50)
        self.assertEqual(mailing_b.opened_ratio, 16)

        with self.mock_mail_gateway():
            ab_testing.action_send_winner_mailing()
        ab_testing.mailing_ids.invalidate_cache()
        winner_mailing = ab_testing.mailing_ids.filtered(lambda mailing: mailing.is_winner)
        self.assertEqual(ab_testing.state, 'done')
        self.assertEqual(winner_mailing.subject, 'Test 1')
        self.assertEqual(winner_mailing.version_id.name, 'A - Final')
        self.assertEqual(winner_mailing.contact_ab_pc, 0.75)
        self.assertEqual(mailing_a.contact_ab_pc, 0.125)
        self.assertEqual(mailing_b.contact_ab_pc, 0.125)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_ab_testing_manual_flow(self):
        ab_testing = self._create_ab_testing_mailings(2, 'manual')
        mailing_a = ab_testing.mailing_ids[0]
        mailing_b = ab_testing.mailing_ids[1]
        self.assertEqual(ab_testing.state, 'new')

        self.assertEqual(len(ab_testing.mailing_ids), 2)
        self.assertEqual(ab_testing.mailing_ids[0].contact_ab_pc, 0.125)
        self.assertEqual(ab_testing.mailing_ids[1].contact_ab_pc, 0.125)

        with self.mock_mail_gateway():
            ab_testing.action_send_mailings()
        self.assertEqual(ab_testing.state, 'in_progress')
        self.assertEqual(mailing_a.state, 'done')
        self.assertEqual(mailing_b.state, 'done')
        self.assertEqual(mailing_a.opened_ratio, 0)
        self.assertEqual(mailing_b.opened_ratio, 0)

        total_traces = mailing_a.mailing_trace_ids + mailing_b.mailing_trace_ids
        unique_recipients_used = set(map(lambda mail: mail.res_id, total_traces.mail_mail_id))
        self.assertEqual(len(mailing_a.mailing_trace_ids), 18)
        self.assertEqual(len(mailing_b.mailing_trace_ids), 18)
        self.assertEqual(len(unique_recipients_used), 36)

        mailing_a.mailing_trace_ids[:9].set_opened()
        mailing_b.mailing_trace_ids[:3].set_opened()
        ab_testing.mailing_ids.invalidate_cache()

        self.assertEqual(mailing_a.opened_ratio, 50)
        self.assertEqual(mailing_b.opened_ratio, 16)

        with self.mock_mail_gateway():
            mailing_b.action_select_as_winner()
        ab_testing.mailing_ids.invalidate_cache()
        winner_mailing = ab_testing.mailing_ids.filtered(lambda mailing: mailing.is_winner)
        self.assertEqual(ab_testing.state, 'done')
        self.assertEqual(winner_mailing.subject, 'Test 2')
        self.assertEqual(winner_mailing.version_id.name, 'B - Final')
        self.assertEqual(winner_mailing.contact_ab_pc, 0.75)
        self.assertEqual(mailing_a.contact_ab_pc, 0.125)
        self.assertEqual(mailing_b.contact_ab_pc, 0.125)
