# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import Form, users


class TestPartner(MailCommon):

    def test_res_partner_find_or_create(self):
        Partner = self.env['res.partner']

        existing = Partner.create({
            'name': 'Patrick Poilvache',
            'email': '"Patrick Da Beast Poilvache" <PATRICK@example.com>',
        })
        self.assertEqual(existing.name, 'Patrick Poilvache')
        self.assertEqual(existing.email, '"Patrick Da Beast Poilvache" <PATRICK@example.com>')
        self.assertEqual(existing.email_normalized, 'patrick@example.com')

        new = Partner.find_or_create('Patrick Caché <patrick@EXAMPLE.COM>')
        self.assertEqual(new, existing)

        new2 = Partner.find_or_create('Patrick Caché <2patrick@EXAMPLE.COM>')
        self.assertTrue(new2.id > new.id)
        self.assertEqual(new2.name, 'Patrick Caché')
        self.assertEqual(new2.email, '2patrick@example.com')
        self.assertEqual(new2.email_normalized, '2patrick@example.com')

    @users('admin')
    def test_res_partner_merge_wizards(self):
        Partner = self.env['res.partner']

        p1 = Partner.create({'name': 'Customer1', 'email': 'test1@test.example.com'})
        p1_msg_ids_init = p1.message_ids
        p2 = Partner.create({'name': 'Customer2', 'email': 'test2@test.example.com'})
        p2_msg_ids_init = p2.message_ids
        p3 = Partner.create({'name': 'Other (dup email)', 'email': 'test1@test.example.com'})

        # add some mail related documents
        p1.message_subscribe(partner_ids=p3.ids)
        p1_act1 = p1.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo')
        p1_msg1 = p1.message_post(
            body='<p>Log on P1</p>',
            subtype_id=self.env.ref('mail.mt_comment').id
        )
        self.assertEqual(p1.activity_ids, p1_act1)
        self.assertEqual(p1.message_follower_ids.partner_id, self.partner_admin + p3)
        self.assertEqual(p1.message_ids, p1_msg_ids_init + p1_msg1)
        self.assertEqual(p2.activity_ids, self.env['mail.activity'])
        self.assertEqual(p2.message_follower_ids.partner_id, self.partner_admin)
        self.assertEqual(p2.message_ids, p2_msg_ids_init)

        MergeForm = Form(self.env['base.partner.merge.automatic.wizard'].with_context(
            active_model='res.partner',
            active_ids=(p1 + p2).ids
        ))
        self.assertEqual(MergeForm.partner_ids[:], p1 + p2)
        self.assertEqual(MergeForm.dst_partner_id, p2)
        merge_form = MergeForm.save()
        merge_form.action_merge()

        # check destination and removal
        self.assertFalse(p1.exists())
        self.assertTrue(p2.exists())
        # check mail documents have been moved
        self.assertEqual(p2.activity_ids, p1_act1)
        # TDE note: currently not working as soon as there is a single partner duplicated -> should be improved
        # self.assertEqual(p2.message_follower_ids.partner_id, self.partner_admin + p3)
        all_msg = p2_msg_ids_init + p1_msg_ids_init + p1_msg1
        self.assertEqual(len(p2.message_ids), len(all_msg) + 1, 'Should have original messages + a log')
        self.assertTrue(all(msg in p2.message_ids for msg in all_msg))
