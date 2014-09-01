# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.addons.mail.tests.common import TestMail


class test_mail_access_rights(TestMail):

    def test_00_message_read(self):
        """ Tests for message_read and expandables. """
        cr, uid, user_admin, user_raoul, group_pigs = self.cr, self.uid, self.user_admin, self.user_raoul, self.group_pigs
        self.mail_group.message_subscribe_users(cr, uid, [group_pigs.id], [user_raoul.id])
        pigs_domain = [('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs_id)]

        # Data: create a discussion in Pigs (3 threads, with respectively 0, 4 and 4 answers)
        msg_id0 = self.group_pigs.message_post(body='0', subtype='mt_comment')
        msg_id1 = self.group_pigs.message_post(body='1', subtype='mt_comment')
        msg_id2 = self.group_pigs.message_post(body='2', subtype='mt_comment')
        msg_id3 = self.group_pigs.message_post(body='1-1', subtype='mt_comment', parent_id=msg_id1)
        msg_id4 = self.group_pigs.message_post(body='2-1', subtype='mt_comment', parent_id=msg_id2)
        msg_id5 = self.group_pigs.message_post(body='1-2', subtype='mt_comment', parent_id=msg_id1)
        msg_id6 = self.group_pigs.message_post(body='2-2', subtype='mt_comment', parent_id=msg_id2)
        msg_id7 = self.group_pigs.message_post(body='1-1-1', subtype='mt_comment', parent_id=msg_id3)
        msg_id8 = self.group_pigs.message_post(body='2-1-1', subtype='mt_comment', parent_id=msg_id4)
        msg_id9 = self.group_pigs.message_post(body='1-1-1', subtype='mt_comment', parent_id=msg_id3)
        msg_id10 = self.group_pigs.message_post(body='2-1-1', subtype='mt_comment', parent_id=msg_id4)
        msg_ids = [msg_id10, msg_id9, msg_id8, msg_id7, msg_id6, msg_id5, msg_id4, msg_id3, msg_id2, msg_id1, msg_id0]
        ordered_msg_ids = [msg_id2, msg_id4, msg_id6, msg_id8, msg_id10, msg_id1, msg_id3, msg_id5, msg_id7, msg_id9, msg_id0]

        # Test: raoul received notifications
        raoul_notification_ids = self.mail_notification.search(cr, user_raoul.id, [('is_read', '=', False), ('message_id', 'in', msg_ids), ('partner_id', '=', user_raoul.partner_id.id)])
        self.assertEqual(len(raoul_notification_ids), 11, 'message_post: wrong number of produced notifications')

        # Test: read some specific ids
        read_msg_list = self.mail_message.message_read(cr, user_raoul.id, ids=msg_ids[2:4], domain=[('body', 'like', 'dummy')], context={'mail_read_set_read': True})
        read_msg_ids = [msg.get('id') for msg in read_msg_list]
        self.assertEqual(msg_ids[2:4], read_msg_ids, 'message_read with direct ids should read only the requested ids')

        # Test: read messages of Pigs through a domain, being thread or not threaded
        read_msg_list = self.mail_message.message_read(cr, user_raoul.id, domain=pigs_domain, limit=200)
        read_msg_ids = [msg.get('id') for msg in read_msg_list]
        self.assertEqual(msg_ids, read_msg_ids, 'message_read flat with domain on Pigs should equal all messages of Pigs')
        read_msg_list = self.mail_message.message_read(cr, user_raoul.id, domain=pigs_domain, limit=200, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in read_msg_list]
        self.assertEqual(ordered_msg_ids, read_msg_ids,
            'message_read threaded with domain on Pigs should equal all messages of Pigs, and sort them with newer thread first, last message last in thread')

        # ----------------------------------------
        # CASE1: message_read with domain, threaded
        # We simulate an entire flow, using the expandables to test them
        # ----------------------------------------

        # Do: read last message, threaded
        read_msg_list = self.mail_message.message_read(cr, uid, domain=pigs_domain, limit=1, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # TDE TODO: test expandables order
        type_list = map(lambda item: item.get('type'), read_msg_list)
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(read_msg_list), 4, 'message_read on last Pigs message should return 2 messages and 2 expandables')
        self.assertEqual(set([msg_id2, msg_id10]), set(read_msg_ids), 'message_read on the last Pigs message should also get its parent')
        self.assertEqual(read_msg_list[1].get('parent_id'), read_msg_list[0].get('id'), 'message_read should set the ancestor to the thread header')
        # Data: get expandables
        new_threads_exp, new_msg_exp = None, None
        for msg in read_msg_list:
            if msg.get('type') == 'expandable' and msg.get('nb_messages') == -1 and msg.get('max_limit'):
                new_threads_exp = msg
            elif msg.get('type') == 'expandable':
                new_msg_exp = msg

        # Do: fetch new messages in first thread, domain from expandable
        self.assertIsNotNone(new_msg_exp, 'message_read on last Pigs message should have returned a new messages expandable')
        domain = new_msg_exp.get('domain', [])
        # Test: expandable, conditions in domain
        self.assertIn(('id', 'child_of', msg_id2), domain, 'new messages expandable domain should contain a child_of condition')
        self.assertIn(('id', '>=', msg_id4), domain, 'new messages expandable domain should contain an id greater than condition')
        self.assertIn(('id', '<=', msg_id8), domain, 'new messages expandable domain should contain an id less than condition')
        self.assertEqual(new_msg_exp.get('parent_id'), msg_id2, 'new messages expandable should have parent_id set to the thread header')
        # Do: message_read with domain, thread_level=0, parent_id=msg_id2 (should be imposed by JS), 2 messages
        read_msg_list = self.mail_message.message_read(cr, uid, domain=domain, limit=2, thread_level=0, parent_id=msg_id2)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        new_msg_exp = [msg for msg in read_msg_list if msg.get('type') == 'expandable'][0]
        # Test: structure content, 2 messages and 1 thread expandable
        self.assertEqual(len(read_msg_list), 3, 'message_read in Pigs thread should return 2 messages and 1 expandables')
        self.assertEqual(set([msg_id6, msg_id8]), set(read_msg_ids), 'message_read in Pigs thread should return 2 more previous messages in thread')
        # Do: read the last message
        read_msg_list = self.mail_message.message_read(cr, uid, domain=new_msg_exp.get('domain'), limit=2, thread_level=0, parent_id=msg_id2)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # Test: structure content, 1 message
        self.assertEqual(len(read_msg_list), 1, 'message_read in Pigs thread should return 1 message')
        self.assertEqual(set([msg_id4]), set(read_msg_ids), 'message_read in Pigs thread should return the last message in thread')

        # Do: fetch a new thread, domain from expandable
        self.assertIsNotNone(new_threads_exp, 'message_read on last Pigs message should have returned a new threads expandable')
        domain = new_threads_exp.get('domain', [])
        # Test: expandable, conditions in domain
        for condition in pigs_domain:
            self.assertIn(condition, domain, 'new threads expandable domain should contain the message_read domain parameter')
        self.assertFalse(new_threads_exp.get('parent_id'), 'new threads expandable should not have an parent_id')
        # Do: message_read with domain, thread_level=1 (should be imposed by JS)
        read_msg_list = self.mail_message.message_read(cr, uid, domain=domain, limit=1, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(read_msg_list), 4, 'message_read on Pigs should return 2 messages and 2 expandables')
        self.assertEqual(set([msg_id1, msg_id9]), set(read_msg_ids), 'message_read on a Pigs message should also get its parent')
        self.assertEqual(read_msg_list[1].get('parent_id'), read_msg_list[0].get('id'), 'message_read should set the ancestor to the thread header')
        # Data: get expandables
        new_threads_exp, new_msg_exp = None, None
        for msg in read_msg_list:
            if msg.get('type') == 'expandable' and msg.get('nb_messages') == -1 and msg.get('max_limit'):
                new_threads_exp = msg
            elif msg.get('type') == 'expandable':
                new_msg_exp = msg

        # Do: fetch new messages in second thread, domain from expandable
        self.assertIsNotNone(new_msg_exp, 'message_read on Pigs message should have returned a new messages expandable')
        domain = new_msg_exp.get('domain', [])
        # Test: expandable, conditions in domain
        self.assertIn(('id', 'child_of', msg_id1), domain, 'new messages expandable domain should contain a child_of condition')
        self.assertIn(('id', '>=', msg_id3), domain, 'new messages expandable domain should contain an id greater than condition')
        self.assertIn(('id', '<=', msg_id7), domain, 'new messages expandable domain should contain an id less than condition')
        self.assertEqual(new_msg_exp.get('parent_id'), msg_id1, 'new messages expandable should have ancestor_id set to the thread header')
        # Do: message_read with domain, thread_level=0, parent_id=msg_id1 (should be imposed by JS)
        read_msg_list = self.mail_message.message_read(cr, uid, domain=domain, limit=200, thread_level=0, parent_id=msg_id1)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # Test: other message in thread have been fetch
        self.assertEqual(set([msg_id3, msg_id5, msg_id7]), set(read_msg_ids), 'message_read on the last Pigs message should also get its parent')

        # Test: fetch a new thread, domain from expandable
        self.assertIsNotNone(new_threads_exp, 'message_read should have returned a new threads expandable')
        domain = new_threads_exp.get('domain', [])
        # Test: expandable, conditions in domain
        for condition in pigs_domain:
            self.assertIn(condition, domain, 'general expandable domain should contain the message_read domain parameter')
        # Do: message_read with domain, thread_level=1 (should be imposed by JS)
        read_msg_list = self.mail_message.message_read(cr, uid, domain=domain, limit=1, thread_level=1)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(read_msg_list), 1, 'message_read on Pigs should return 1 message because everything else has been fetched')
        self.assertEqual([msg_id0], read_msg_ids, 'message_read after 2 More should return only 1 last message')

        # ----------------------------------------
        # CASE2: message_read with domain, flat
        # ----------------------------------------

        # Do: read 2 lasts message, flat
        read_msg_list = self.mail_message.message_read(cr, uid, domain=pigs_domain, limit=2, thread_level=0)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is not set, 1 expandable
        self.assertEqual(len(read_msg_list), 3, 'message_read on last Pigs message should return 2 messages and 1 expandable')
        self.assertEqual(set([msg_id9, msg_id10]), set(read_msg_ids), 'message_read flat on Pigs last messages should only return those messages')
        self.assertFalse(read_msg_list[0].get('parent_id'), 'message_read flat should set the ancestor as False')
        self.assertFalse(read_msg_list[1].get('parent_id'), 'message_read flat should set the ancestor as False')
        # Data: get expandables
        new_threads_exp, new_msg_exp = None, None
        for msg in read_msg_list:
            if msg.get('type') == 'expandable' and msg.get('nb_messages') == -1 and msg.get('max_limit'):
                new_threads_exp = msg

        # Do: fetch new messages, domain from expandable
        self.assertIsNotNone(new_threads_exp, 'message_read flat on the 2 last Pigs messages should have returns a new threads expandable')
        domain = new_threads_exp.get('domain', [])
        # Test: expandable, conditions in domain
        for condition in pigs_domain:
            self.assertIn(condition, domain, 'new threads expandable domain should contain the message_read domain parameter')
        # Do: message_read with domain, thread_level=0 (should be imposed by JS)
        read_msg_list = self.mail_message.message_read(cr, uid, domain=domain, limit=20, thread_level=0)
        read_msg_ids = [msg.get('id') for msg in read_msg_list if msg.get('type') != 'expandable']
        # Test: structure content, ancestor is added to the read messages, ordered by id, ancestor is set, 2 expandables
        self.assertEqual(len(read_msg_list), 9, 'message_read on Pigs should return 9 messages and 0 expandable')
        self.assertEqual([msg_id8, msg_id7, msg_id6, msg_id5, msg_id4, msg_id3, msg_id2, msg_id1, msg_id0], read_msg_ids,
            'message_read, More on flat, should return all remaning messages')
