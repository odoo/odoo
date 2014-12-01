# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.tests import common

class TestNote(common.TransactionCase):

    def setUp(self):
        super(TestNote, self).setUp()

        Note = self.env['note.note']
        Stage = self.env['note.stage']
        User = self.env['res.users']
        group_employee_id = self.ref('base.group_user')

        # Test users
        self.user1 = User.create({
            'name': 'Arielle Dombasle',
            'login': 'Arielle',
            'alias_name': 'arielle',
            'email': 'arielle.dombasle@example.com',
            'groups_id': [(6, 0, [group_employee_id])]
        })
        self.user2 = User.create({
            'name': 'Philippe Katerine',
            'login': 'Philippe',
            'alias_name': 'philippe',
            'email': 'philippe.katerine@example.com',
            'groups_id': [(6, 0, [group_employee_id])]
        })

        # Test stages
        self.stage11 = Stage.create({
                'name': 'arielle_1',
                'user_id': self.user1.id
                })
        self.stage12 = Stage.create({
                'name': 'arielle_2',
                'user_id': self.user1.id
                })
        self.stage21 = Stage.create({
                'name': 'phil_1',
                'user_id': self.user2.id
                })
        self.stage22 = Stage.create({
                'name': 'phil_2',
                'user_id': self.user2.id
                })

        # Test notes
        self.note1 = Note.create({
                'user_id': self.user1.id,
                'memo': '<p>Ceci est une note</p>',
                'sequence': 1,
                'message_follower_ids': [self.user1.partner_id.id, self.user2.partner_id.id],
                'stage_ids': [(6,0,[self.stage11.id, self.stage21.id])]
                })
        self.note2 = Note.create({
                'user_id': self.user2.id,
                'memo': '<p>Ceci est peut-etre une note</p><br/><p>Ou pas!</p>',
                'sequence': 3,
                'message_follower_ids': [self.user1.partner_id.id, self.user2.partner_id.id],
                'stage_ids': [(6,0,[self.stage12.id, self.stage22.id])]
                })

    # TESTS
    # note.note: title from first line of content
    #            done/not done
    #            note stage per user

    def test_note_title(self):
        """ Test: Note title is equals to first line withtout html tags """
        self.assertEqual(self.note1.name,'Ceci est une note')
        self.assertEqual(self.note2.name,'Ceci est peut-etre une note')

    def test_note_done(self):
        """ Test: Done/Not Done switch """
        self.note1.onclick_note_is_done()
        self.assertTrue(self.note1.open==False and self.note1.date_done!=None)
        self.note1.onclick_note_not_done()
        self.assertTrue(self.note1.open)

    def test_user_stage(self):
        """ Test: Note stage is user dependent """
        stage1 = self.env['note.note'].sudo(self.user1).browse(self.note1.id).stage_id
        stage2 = self.env['note.note'].sudo(self.user2).browse(self.note1.id).stage_id
        self.assertTrue(stage1 != stage2)
