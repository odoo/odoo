from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestUnifiedRead(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.only_course_user = new_test_user(cls.env, 'no acc', 'base.group_public')
        cls.author = cls.env['test_new_api.person'].create({'name': 'ged'})
        cls.teacher = cls.env['test_new_api.person'].create({'name': 'aab'})
        cls.course = cls.env['test_new_api.course'].create({
            'name': 'introduction to OWL',
            'author_id': cls.author.id
        })
        cls.lesson_day1 = cls.env['test_new_api.lesson'].create({
            'name': 'first day',
            'date': fields.Date.today(),
            'course_id': cls.course.id,
            'teacher_id': cls.teacher.id,
            'attendee_ids': [Command.create({'name': '123'}),
                             Command.create({'name': '456'}),
                             Command.create({'name': '789'})]
        })
        cls.lesson_day2 = cls.env['test_new_api.lesson'].create({
            'name': 'second day',
            'date': fields.Date.today() + relativedelta(days=1),
            'course_id': cls.course.id,
            'teacher_id': cls.teacher.id
        })

        cls.course_no_author = cls.env['test_new_api.course'].create({'name': 'some other course without author'})

    def test_read_add_id(self):
        read = self.course.read({'display_name': {}})
        self.assertEqual(read, [{'id': self.course.id, 'display_name': 'introduction to OWL'}])

    def test_read_many2one_gives_id(self):
        read = self.course.read({'display_name': {}, 'author_id': {}})
        self.assertEqual(read, [
            {'id': self.course.id,
             'display_name': 'introduction to OWL',
             'author_id': self.author.id}])

    def test_read_many2one_gives_id_2(self):
        read = self.course.read({'display_name': {}, 'author_id': {'fields': {}}})
        self.assertEqual(read, [
            {'id': self.course.id,
             'display_name': 'introduction to OWL',
             'author_id': self.author.id}])

    def test_read_many2one_can_read_extra_fields(self):
        read = self.course.read({'display_name': {}, 'author_id': {'fields': {'write_date': {}}}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'author_id': {'id': self.author.id, 'write_date': self.author.write_date}
            }
        ])

    def test_read_many2one_throws_if_it_cannot_read_extra_fields(self):
        with self.assertRaises(AccessError):
            self.course.with_user(self.only_course_user).read(
                {
                    'display_name': {},
                    'author_id':
                        {
                            'fields': {'write_date': {}}
                        }
                })

    def test_read_many2one_gives_false_if_no_value(self):
        read = self.course_no_author.read({'display_name': {}, 'author_id': {}})
        self.assertEqual(read, [
            {'id': self.course_no_author.id,
             'display_name': 'some other course without author',
             'author_id': False}])

    def test_read_many2one_gives_id_name(self):
        read = self.course.read({'display_name': {}, 'author_id': {'fields': {'display_name': {}}}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'author_id': {
                    'id': self.author.id,
                    'display_name': 'ged'
                }
            }
        ])

    def test_read_many2one_gives_id_name_even_if_you_dont_have_access(self):
        read = self.course.with_user(self.only_course_user).read(
            {'display_name': {}, 'author_id': {'fields': {'display_name': {}}}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'author_id': {
                    'id': self.author.id,
                    'display_name': 'ged'
                }
            }
        ])

    def test_many2one_respects_context(self):
        read = self.course.read(

            {
                'display_name': {},
                'author_id':
                    {
                        'fields': {'display_name': {}},
                        'context': {'special': 'absolutely'}
                    }
            })

        self.assertEqual(read, [

            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'author_id': {
                    'id': self.author.id,
                    'display_name': 'ged special'
                }
            }])

    def test_read_one2many_gives_ids(self):
        read = self.course.read({'display_name': {}, 'lesson_ids': {}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids': [self.lesson_day1.id, self.lesson_day2.id]
            }])

    def test_specify_fields_one2many(self):
        read = self.course.read(
            {
                'display_name': {},
                'lesson_ids':
                    {
                        'fields': {'display_name': {}}
                    }
            })

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {'id': self.lesson_day1.id, 'display_name': 'first day'},
                        {'id': self.lesson_day2.id, 'display_name': 'second day'}
                    ],
            }])

    def test_one2many_context_have_no_impact_on_name(self):
        read = self.course._read_main(
            {
                'name': {},
                'lesson_ids':
                    {
                        'fields': {'name': {}},
                        'context': {'special': 'absolutely'}
                    }
            })

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {'id': self.lesson_day1.id, 'name': 'first day'},
                        {'id': self.lesson_day2.id, 'name': 'second day'}
                    ]
                ,
            }])

    def test_one2many_respects_context(self):
        read = self.course._read_main(
            {
                'display_name': {},
                'lesson_ids':
                    {
                        'fields': {'display_name': {}},
                        'context': {'special': 'absolutely'}
                    }
            })

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {'id': self.lesson_day1.id, 'display_name': 'special first day'},
                        {'id': self.lesson_day2.id, 'display_name': 'special second day'}
                    ],
            }])

    def test_read_many2many_gives_ids(self):
        read = self.course.read({'display_name': {},
                                 'lesson_ids': {
                                     'fields': {
                                         'attendee_ids': {}
                                     }
                                 }})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {'id': self.lesson_day1.id, 'attendee_ids': [*self.lesson_day1.attendee_ids._ids]},
                        {'id': self.lesson_day2.id, 'attendee_ids': []}
                    ],
            }])

    def test_specify_fields_many2many(self):
        read = self.course.read({'display_name': {},
                                 'lesson_ids': {
                                     'fields': {
                                         'attendee_ids': {
                                             'fields': {
                                                 'display_name': {}
                                             }
                                         }
                                     }
                                 }})

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {
                            'id': self.lesson_day1.id,
                            'attendee_ids':
                                [
                                    {'id': self.lesson_day1.attendee_ids._ids[0], 'display_name': '123'},
                                    {'id': self.lesson_day1.attendee_ids._ids[1], 'display_name': '456'},
                                    {'id': self.lesson_day1.attendee_ids._ids[2], 'display_name': '789'}
                                ],
                        },
                        {'id': self.lesson_day2.id, 'attendee_ids': []}
                    ]
            }])

    def test_many2many_respects_limit(self):
        read = self.course.read({'display_name': {},
                                 'lesson_ids': {
                                     'fields': {
                                         'attendee_ids': {
                                             'offset': 0,
                                             'limit': 2,
                                             'fields': {
                                                 'display_name': {}
                                             }
                                         }
                                     }
                                 }})

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {
                            'id': self.lesson_day1.id,
                            'attendee_ids':
                                [
                                    {'id': self.lesson_day1.attendee_ids._ids[0], 'display_name': '123'},
                                    {'id': self.lesson_day1.attendee_ids._ids[1], 'display_name': '456'},
                                    {'id': self.lesson_day1.attendee_ids._ids[2]}
                                ],
                        },
                        {'id': self.lesson_day2.id, 'attendee_ids': []}
                    ]
            }])

    def test_many2many_respects_offset(self):
        read = self.course.read({'display_name': {},
                                 'lesson_ids': {
                                     'fields': {
                                         'attendee_ids': {
                                             'limit': 2,
                                             'offset': 1,
                                             'fields': {
                                                 'display_name': {}
                                             }
                                         }
                                     }
                                 }})

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {
                            'id': self.lesson_day1.id,
                            'attendee_ids':
                                [
                                    {'id': self.lesson_day1.attendee_ids._ids[0]},
                                    {'id': self.lesson_day1.attendee_ids._ids[1], 'display_name': '456'},
                                    {'id': self.lesson_day1.attendee_ids._ids[2], 'display_name': '789'}
                                ],
                        },
                        {'id': self.lesson_day2.id, 'attendee_ids': []}
                    ]
            }])

    def test_many2many_limits_with_deleted_records(self):
        # should we ignore this ? in the python we will not use the limits, and in the RPC we won't delete and read in the same transaction with limits
        pass

    def test_many2many_respects_order(self):
        pass
