# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail
from openerp.tools import mute_logger


class TestMessageRead(TestMail):

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def setUp(self):
        super(TestMessageRead, self).setUp()
        self.group_pigs.message_subscribe_users([self.user_employee.id])
        self.msg_0 = self.group_pigs.message_post(body='0', subtype='mt_comment')
        self.msg_1 = self.group_pigs.message_post(body='1', subtype='mt_comment')
        self.msg_2 = self.group_pigs.message_post(body='2', subtype='mt_comment')
        self.msg_3 = self.group_pigs.message_post(body='1-1', subtype='mt_comment', parent_id=self.msg_1.id)
        self.msg_4 = self.group_pigs.message_post(body='2-1', subtype='mt_comment', parent_id=self.msg_2.id)
        self.msg_5 = self.group_pigs.message_post(body='1-2', subtype='mt_comment', parent_id=self.msg_1.id)
        self.msg_6 = self.group_pigs.message_post(body='2-2', subtype='mt_comment', parent_id=self.msg_2.id)
        self.msg_7 = self.group_pigs.message_post(body='1-1-1', subtype='mt_comment', parent_id=self.msg_3.id)
        self.msg_8 = self.group_pigs.message_post(body='2-1-1', subtype='mt_comment', parent_id=self.msg_4.id)
        self.msg_9 = self.group_pigs.message_post(body='1-1-1', subtype='mt_comment', parent_id=self.msg_3.id)
        self.msg_10 = self.group_pigs.message_post(body='2-1-1', subtype='mt_comment', parent_id=self.msg_4.id)
        self.msg_ids = [self.msg_10.id, self.msg_9.id, self.msg_8.id, self.msg_7.id, self.msg_6.id, self.msg_5.id, self.msg_4.id, self.msg_3.id, self.msg_2.id, self.msg_1.id, self.msg_0.id]
        self.ordered_msg_ids = [self.msg_2.id, self.msg_4.id, self.msg_6.id, self.msg_8.id, self.msg_10.id, self.msg_1.id, self.msg_3.id, self.msg_5.id, self.msg_7.id, self.msg_9.id, self.msg_0.id]

        # TODO: with_context({'mail_read_set_read': True})

    def test_message_read_ids(self):
        """ message_read: test reading specific ids """
        messages = self.env['mail.message'].sudo(self.user_employee).browse(self.msg_ids[2:4]).message_read(domain=[('body', 'like', 'dummy')])
        read_msg_ids = [msg.get('id') for msg in messages]
        self.assertEqual(read_msg_ids, self.msg_ids[2:4], 'message_read with direct ids should read only the requested ids')

    def test_message_read_domain(self):
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)], limit=200)
        read_msg_ids = [msg.get('id') for msg in messages]
        self.assertEqual(read_msg_ids, self.msg_ids, 'message_read flat with domain on Pigs should equal all messages of Pigs')

    def test_message_read_domain_thread(self):
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)], limit=200, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in messages]
        self.assertEqual(read_msg_ids, self.ordered_msg_ids, 'message_read threaded with domain on Pigs should equal all messages of Pigs, and sort them with newer thread first, last message last in thread')

    def test_message_read_expandable(self):
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)], limit=1, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # TDE TODO: test expandables order
        type_list = map(lambda item: item.get('type'), messages)
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(messages), 4, 'message_read on last Pigs message should return 2 messages and 2 expandables')
        self.assertEqual(set([self.msg_2.id, self.msg_10.id]), set(read_msg_ids), 'message_read on the last Pigs message should also get its parent')
        self.assertEqual(messages[1].get('parent_id'), messages[0].get('id'), 'message_read should set the ancestor to the thread header')
        # Data: get expandables
        new_threads_exp, new_msg_exp = None, None
        for msg in messages:
            if msg.get('type') == 'expandable' and msg.get('nb_messages') == -1 and msg.get('max_limit'):
                new_threads_exp = msg
            elif msg.get('type') == 'expandable':
                new_msg_exp = msg

        # Do: fetch new messages in first thread, domain from expandable
        self.assertIsNotNone(new_msg_exp, 'message_read on last Pigs message should have returned a new messages expandable')
        domain = new_msg_exp.get('domain', [])
        # Test: expandable, conditions in domain
        self.assertIn(('id', 'child_of', self.msg_2.id), domain, 'new messages expandable domain should contain a child_of condition')
        self.assertIn(('id', '>=', self.msg_4.id), domain, 'new messages expandable domain should contain an id greater than condition')
        self.assertIn(('id', '<=', self.msg_8.id), domain, 'new messages expandable domain should contain an id less than condition')
        self.assertEqual(new_msg_exp.get('parent_id'), self.msg_2.id, 'new messages expandable should have parent_id set to the thread header')
        # Do: message_read with domain, thread_level=0, parent_id=msg_id2 (should be imposed by JS), 2 messages
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=domain, limit=2, thread_level=0, parent_id=self.msg_2.id)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        new_msg_exp = [msg for msg in messages if msg.get('type') == 'expandable'][0]
        # Test: structure content, 2 messages and 1 thread expandable
        self.assertEqual(len(messages), 3, 'message_read in Pigs thread should return 2 messages and 1 expandables')
        self.assertEqual(set([self.msg_6.id, self.msg_8.id]), set(read_msg_ids), 'message_read in Pigs thread should return 2 more previous messages in thread')
        # Do: read the last message
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=new_msg_exp.get('domain'), limit=2, thread_level=0, parent_id=self.msg_2.id)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # Test: structure content, 1 message
        self.assertEqual(len(messages), 1, 'message_read in Pigs thread should return 1 message')
        self.assertEqual(set([self.msg_4.id]), set(read_msg_ids), 'message_read in Pigs thread should return the last message in thread')
        # Do: fetch a new thread, domain from expandable
        self.assertIsNotNone(new_threads_exp, 'message_read on last Pigs message should have returned a new threads expandable')
        domain = new_threads_exp.get('domain', [])
        # Test: expandable, conditions in domain
        for condition in [('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)]:
            self.assertIn(condition, domain, 'new threads expandable domain should contain the message_read domain parameter')
        self.assertFalse(new_threads_exp.get('parent_id'), 'new threads expandable should not have an parent_id')
        # Do: message_read with domain, thread_level=1 (should be imposed by JS)
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=domain, limit=1, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(messages), 4, 'message_read on Pigs should return 2 messages and 2 expandables')
        self.assertEqual(set([self.msg_1.id, self.msg_9.id]), set(read_msg_ids), 'message_read on a Pigs message should also get its parent')
        self.assertEqual(messages[1].get('parent_id'), messages[0].get('id'), 'message_read should set the ancestor to the thread header')
        # Data: get expandables
        new_threads_exp, new_msg_exp = None, None
        for msg in messages:
            if msg.get('type') == 'expandable' and msg.get('nb_messages') == -1 and msg.get('max_limit'):
                new_threads_exp = msg
            elif msg.get('type') == 'expandable':
                new_msg_exp = msg
        # Do: fetch new messages in second thread, domain from expandable
        self.assertIsNotNone(new_msg_exp, 'message_read on Pigs message should have returned a new messages expandable')
        domain = new_msg_exp.get('domain', [])
        # Test: expandable, conditions in domain
        self.assertIn(('id', 'child_of', self.msg_1.id), domain, 'new messages expandable domain should contain a child_of condition')
        self.assertIn(('id', '>=', self.msg_3.id), domain, 'new messages expandable domain should contain an id greater than condition')
        self.assertIn(('id', '<=', self.msg_7.id), domain, 'new messages expandable domain should contain an id less than condition')
        self.assertEqual(new_msg_exp.get('parent_id'), self.msg_1.id, 'new messages expandable should have ancestor_id set to the thread header')
        # Do: message_read with domain, thread_level=0, parent_id=msg_id1 (should be imposed by JS)
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=domain, limit=200, thread_level=0, parent_id=self.msg_1.id)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # Test: other message in thread have been fetch
        self.assertEqual(set([self.msg_3.id, self.msg_5.id, self.msg_7.id]), set(read_msg_ids), 'message_read on the last Pigs message should also get its parent')

        # Test: fetch a new thread, domain from expandable
        self.assertIsNotNone(new_threads_exp, 'message_read should have returned a new threads expandable')
        domain = new_threads_exp.get('domain', [])
        # Test: expandable, conditions in domain
        for condition in [('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)]:
            self.assertIn(condition, domain, 'general expandable domain should contain the message_read domain parameter')
        # Do: message_read with domain, thread_level=1 (should be imposed by JS)
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=domain, limit=1, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(messages), 1, 'message_read on Pigs should return 1 message because everything else has been fetched')
        self.assertEqual([self.msg_0.id], read_msg_ids, 'message_read after 2 More should return only 1 last message')

        # ----------------------------------------
        # CASE2: message_read with domain, flat
        # ----------------------------------------

        # Do: read 2 lasts message, flat
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)], limit=2, thread_level=0)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is not set, 1 expandable
        self.assertEqual(len(messages), 3, 'message_read on last Pigs message should return 2 messages and 1 expandable')
        self.assertEqual(set([self.msg_9.id, self.msg_10.id]), set(read_msg_ids), 'message_read flat on Pigs last messages should only return those messages')
        self.assertFalse(messages[0].get('parent_id'), 'message_read flat should set the ancestor as False')
        self.assertFalse(messages[1].get('parent_id'), 'message_read flat should set the ancestor as False')
        # Data: get expandables
        new_threads_exp, new_msg_exp = None, None
        for msg in messages:
            if msg.get('type') == 'expandable' and msg.get('nb_messages') == -1 and msg.get('max_limit'):
                new_threads_exp = msg
        # Do: fetch new messages, domain from expandable
        self.assertIsNotNone(new_threads_exp, 'message_read flat on the 2 last Pigs messages should have returns a new threads expandable')
        domain = new_threads_exp.get('domain', [])
        # Test: expandable, conditions in domain
        for condition in [('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)]:
            self.assertIn(condition, domain, 'new threads expandable domain should contain the message_read domain parameter')
        # Do: message_read with domain, thread_level=0 (should be imposed by JS)
        messages = self.env['mail.message'].sudo(self.user_employee).message_read(domain=domain, limit=20, thread_level=0)
        read_msg_ids = [msg.get('id') for msg in messages if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(messages), 9, 'message_read on Pigs should return 9 messages and 0 expandable')
        self.assertEqual([self.msg_8.id, self.msg_7.id, self.msg_6.id, self.msg_5.id, self.msg_4.id, self.msg_3.id, self.msg_2.id, self.msg_1.id, self.msg_0.id], read_msg_ids,
            'message_read, More on flat, should return all remaning messages')
