# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestUnityRead(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.only_course_user = new_test_user(cls.env, 'no acc', 'base.group_public')
        cls.author = cls.env['test_new_api.person'].create({'name': 'ged'})
        cls.teacher = cls.env['test_new_api.person'].create({'name': 'aab'})
        cls.account = cls.env['test_new_api.person.account'].create({
            'person_id': cls.teacher.id,
            'login': 'aab',
        })
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

        cls.course.reference = cls.lesson_day1
        cls.course.m2o_reference_model = cls.lesson_day1._name
        cls.course.m2o_reference_id = cls.lesson_day1.id

        cls.course_no_author = cls.env['test_new_api.course'].create({'name': 'some other course without author'})

        cls.env.invalidate_all()

    def test_read_add_id(self):
        read = self.course.web_read({'display_name': {}})
        self.assertEqual(read, [{'id': self.course.id, 'display_name': 'introduction to OWL'}])

    def test_read_many2one_gives_id(self):
        read = self.course.web_read({'display_name': {}, 'author_id': {}})
        self.assertEqual(read, [
            {'id': self.course.id,
             'display_name': 'introduction to OWL',
             'author_id': self.author.id}])

    def test_read_a_model_does_only_1_query(self):
        with self.assertQueryCount(1):
            self.course.web_read({'display_name': {}, 'author_id': {'fields': {}}})

    def test_read_many2one_gives_id_in_dictionary(self):
        read = self.course.web_read({'display_name': {}, 'author_id': {'fields': {}}})
        self.assertEqual(read, [
            {'id': self.course.id,
             'display_name': 'introduction to OWL',
             'author_id': {'id': self.author.id}}])

    def test_read_many2one_can_read_extra_fields(self):
        read = self.course.web_read({'display_name': {}, 'author_id': {'fields': {'write_date': {}}}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'author_id': {'id': self.author.id, 'write_date': self.author.write_date}
            }
        ])

    def test_many2one_query_count(self):
        with self.assertQueryCount(1        # 1 query for the search of the domain and read course fields
                                   + 1):    # 1 query to read the data of the author
            self.course.web_search_read(domain=(),
                                        specification={'display_name': {}, 'author_id': {'fields': {'write_date': {}}}})

    def test_read_many2one_throws_if_it_cannot_read_extra_fields(self):
        with self.assertRaises(AccessError):
            self.course.with_user(self.only_course_user).web_read(
                {
                    'display_name': {},
                    'author_id':
                        {
                            'fields': {'write_date': {}}
                        }
                })

    def test_read_many2one_gives_false_if_no_value(self):
        read = self.course_no_author.web_read({'display_name': {}, 'author_id': {}})
        self.assertEqual(read, [
            {'id': self.course_no_author.id,
             'display_name': 'some other course without author',
             'author_id': False}])

    def test_read_many2one_gives_id_name(self):
        read = self.course.web_read({'display_name': {}, 'author_id': {'fields': {'display_name': {}}}})
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
        read = self.course.with_user(self.only_course_user).web_read(
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
        read = self.course.web_read(
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

    def test_read_many2one_with_new_record(self):
        values = {'author_id': {'id': self.author.id}}
        new_course = self.course.new(values, origin=self.course)

        # new_course.author_id is a new record
        self.assertTrue(new_course.author_id)
        self.assertFalse(new_course.author_id.id)

        result = new_course.web_read({
            'display_name': {},
            'author_id': {},
        })
        self.assertEqual(result, [
            {
                'id': new_course.id,
                'display_name': 'introduction to OWL',
                'author_id': self.author.id,
            }
        ])

        result = new_course.web_read({
            'display_name': {},
            'author_id': {'fields': {'display_name': {}}},
        })
        self.assertEqual(result, [
            {
                'id': new_course.id,
                'display_name': 'introduction to OWL',
                'author_id': {
                    'id': self.author.id,
                    'display_name': 'ged'
                }
            }
        ])

    def test_new_record_with_inherits(self):
        # virtualize a record
        new_account = self.account.new(origin=self.account)
        self.assertTrue(new_account)
        self.assertFalse(new_account.id)

        # read the virtualized record; field 'id' corresponds to record's origin
        result = new_account.web_read({
            'name': {},
            'login': {},
        })
        self.assertEqual(result, [{
            'id': new_account.id,
            'name': new_account.name,
            'login': new_account.login,
        }])

        # special case: read the many2one field of _inherits
        self.assertTrue(new_account.person_id)
        self.assertFalse(new_account.person_id.id)
        result = new_account.web_read({
            'person_id': {'fields': {'name': {}}},
        })
        self.assertEqual(result, [{
            'id': new_account.id,
            'person_id': {
                'id': new_account.person_id._origin.id,
                'name': new_account.person_id.name,
            },
        }])

    def test_multilevel_query_count(self):
        author = self.env['test_new_api.person'].create({'name': 'AAA'})
        teacher1 = self.env['test_new_api.person'].create({'name': 'BBB'})
        teacher2 = self.env['test_new_api.person'].create({'name': 'FFF'})
        course = self.env['test_new_api.course'].create({
            'name': 'CCC',
            'author_id': author.id
        })
        self.env['test_new_api.lesson'].create({
            'name': 'DDD',
            'course_id': course.id,
            'teacher_id': teacher1.id,
        })
        self.env['test_new_api.lesson'].create({
            'name': 'EEE',
            'course_id': course.id,
            'teacher_id': teacher2.id
        })
        self.env.invalidate_all()
        with self.assertQueryCount(1        # read the course with author id
                                   + 1      # read the lessons of the course
                                   + 1      # read the author name of course
                                   + 1      # ids of the teachers of each lesson
                                   + 1):    # read the teacher name of each lessons in one query
            course.web_read(
                {
                    'display_name': {},
                    'author_id': {'fields': {'display_name': {}}},
                    'lesson_ids':
                        {
                            'fields':
                                {
                                    'teacher_id': {'fields': {'display_name': {}}}
                                }
                        }
                })

    def test_that_contexts_of_many2one_impacts_each_other(self):
        read = self.course.web_read(
            {
                'display_name': {},
                'author_id':
                    {
                        'fields': {'display_name': {}},
                        'context': {'special': 'absolutely'}
                    },
                'lesson_ids':
                    {
                        'fields':
                            {
                                'teacher_id':
                                    {
                                        'fields': {'display_name': {}},
                                        'context': {'particular': 'definitely'}
                                    }
                            }
                    }
            })

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'author_id': {'id': self.author.id, 'display_name': 'ged special'},
                'lesson_ids': [
                    {
                        'id': self.lesson_day1.id,
                        'teacher_id': {'id': self.teacher.id, 'display_name': 'particular aab'}
                    }, {
                        'id': self.lesson_day2.id,
                        'teacher_id': {'id': self.teacher.id, 'display_name': 'particular aab'}
                    },
                ],
            }])

    def test_read_one2many_gives_ids(self):
        read = self.course.web_read({'display_name': {}, 'lesson_ids': {}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids': [self.lesson_day1.id, self.lesson_day2.id]
            }])

    def test_specify_fields_one2many(self):
        read = self.course.web_read(
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
        read = self.course.web_read(
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
                        {'id': self.lesson_day2.id, 'name': 'second day'},
                    ]
            }])

    def test_one2many_respects_context(self):
        read = self.course.web_read(
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
        with self.assertQueryCount(1        # 1 query for course
                                   + 1      # 1 query for the lessons
                                   + 1):    # 1 query for the attendees ids
            read = self.course.web_read({'display_name': {},
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
        read = self.course.web_read({'display_name': {},
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
        read = self.course.web_read({'display_name': {},
                                     'lesson_ids': {
                                         'fields': {
                                             'attendee_ids': {
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

    def test_many2many_limit_has_no_effect_when_no_field_requested(self):
        read = self.course.web_read({'display_name': {},
                                     'lesson_ids': {
                                         'fields': {
                                             'attendee_ids': {
                                                 'limit': 2,
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
                                    self.lesson_day1.attendee_ids._ids[0],
                                    self.lesson_day1.attendee_ids._ids[1],
                                    self.lesson_day1.attendee_ids._ids[2],
                                ],
                        },
                        {'id': self.lesson_day2.id, 'attendee_ids': []}
                    ]
            }])

    def test_many2many_order_has_effect_when_no_field_requested(self):
        read = self.course.web_read({'display_name': {},
                                     'lesson_ids': {
                                         'order': 'name desc'
                                     }})

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'display_name': 'introduction to OWL',
                'lesson_ids':
                    [
                        self.lesson_day2.id,
                        self.lesson_day1.id
                    ]
            }])

    def test_many2many_limits_with_deleted_records(self):
        # should we ignore this ? in the python we will not use the limits, and in the RPC we won't delete and read in the same transaction with limits
        pass

    def test_many2many_respects_order(self):
        read = self.course.web_read(
            {
                'name': {},
                'lesson_ids':
                    {
                        'fields': {'name': {}},
                        'order': 'name desc'
                    }
            })

        self.assertEqual(read, [
            {
                'id': self.course.id,
                'name': 'introduction to OWL',
                'lesson_ids':
                    [
                        {'id': self.lesson_day2.id, 'name': 'second day'},
                        {'id': self.lesson_day1.id, 'name': 'first day'},
                    ]
            }])

    def test_many2many_order_increases_query_count(self):
        with self.assertQueryCount(3):
            self.course.web_read(
                {
                    'name': {},
                    'lesson_ids':
                        {
                            'fields': {'name': {}},
                        }
                })
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            self.course.web_read(
                {
                    'name': {},
                    'lesson_ids':
                        {
                            'fields': {'name': {}},
                            'order': 'name desc'
                        }
                })

    def test_reference_fields_naked(self):
        read = self.course.web_read({'reference': {}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': f"{self.lesson_day1._name},{self.lesson_day1.id}"
            }
        ])

    def test_reference_fields(self):
        read = self.course.web_read({'reference': {'fields': {}}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': {
                    'id': {'id': self.lesson_day1.id, 'model': self.lesson_day1._name},
                }
            }
        ])

    def test_reference_fields_display_name(self):
        read = self.course.web_read({'reference': {'fields': {'display_name': {}}}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': {
                    'id': {'id': self.lesson_day1.id, 'model': self.lesson_day1._name},
                    'display_name': 'first day'
                }
            }
        ])

    def test_reference_fields_respect_context(self):
        read = self.course.web_read(
            {
                'reference':
                    {
                        'fields': {'display_name': {}},
                        'context': {'special': 'yes'}
                    }
            })
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': {
                    'id': {'id': self.lesson_day1.id, 'model': self.lesson_day1._name},
                    'display_name': 'special first day'
                }
            }
        ])

    def test_reference_fields_respect_context_with_new_record(self):
        new_course = self.course.new(origin=self.course)
        read = new_course.web_read(
            {
                'reference':
                    {
                        'fields': {'display_name': {}},
                        'context': {'special': 'yes'}
                    }
            })
        self.assertEqual(read, [
            {
                'id': new_course.id,
                'reference': {
                    'id': {'id': self.lesson_day1.id, 'model': self.lesson_day1._name},
                    'display_name': 'special first day'
                }
            }
        ])

    def test_reference_fields_extra_fields(self):
        read = self.course.web_read(
            {
                'reference':
                    {
                        'fields': {'write_date': {}},
                    }
            })
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': {
                    'id': {'id': self.lesson_day1.id, 'model': self.lesson_day1._name},
                    'write_date': self.lesson_day1.write_date
                }
            }
        ])

    def test_many2one_reference_naked(self):
        read = self.course.web_read({'m2o_reference_id': {},
                                     'm2o_reference_model': {}})
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'm2o_reference_id': self.lesson_day1.id,
                'm2o_reference_model': self.lesson_day1._name,
            }
        ])

    def test_many2one_reference(self):
        read = self.course.web_read(
            {
                'm2o_reference_id':
                    {
                        'fields':
                            {
                                'display_name': {},
                                'write_date': {},
                            },
                        'context':
                            {
                                'special': 'yes',
                            }
                    },
                'm2o_reference_model': {}
            })
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'm2o_reference_id': {
                    'id': self.lesson_day1.id,
                    'display_name': "special first day",
                    'write_date': self.lesson_day1.write_date
                },
                'm2o_reference_model': self.lesson_day1._name,
            }
        ])

    def test_reference_without_values(self):
        read = self.course_no_author.web_read(
            {
                'reference':
                    {
                        'fields': {'write_date': {}},
                    },
                'm2o_reference_id':
                    {
                        'fields':
                            {
                                'display_name': {},
                                'write_date': {},
                            },
                    },
                'm2o_reference_model': {}
            })
        self.assertEqual(read, [
            {
                'id': self.course_no_author.id,
                'reference': False,
                'm2o_reference_id': False,
                'm2o_reference_model': False,
            }
        ])

    def test_reference_with_deleted_record(self):
        self.lesson_day1.unlink()
        read = self.course.web_read(
            {
                'reference': {'fields': {}},
                'm2o_reference_id': {'fields': {}},
                'm2o_reference_model': {}
            })
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': False,
                'm2o_reference_id': False,
                'm2o_reference_model': False,
            }
        ])

    def test_reference_with_deleted_record_no_fields(self):
        """
        When no fields are asked on the reference and many2one_reference fields,
        the raw value of those fields is returned from the database, and no test
        for existence is made.
        """
        self.lesson_day1.unlink()
        read = self.course.web_read(
            {
                'reference': {},
                'm2o_reference_id': {},
                'm2o_reference_model': {}
            })
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': f"{self.lesson_day1._name},{self.lesson_day1.id}",
                'm2o_reference_id': self.lesson_day1.id,
                'm2o_reference_model': self.lesson_day1._name,
            }
        ])

    def test_reference_with_deleted_record_extra_info(self):
        self.lesson_day1.unlink()
        read = self.course.web_read(
            {
                'reference': {'fields': {'display_name': {}}},
                'm2o_reference_id': {'fields': {'display_name': {}}},
                'm2o_reference_model': {}
            })
        self.assertEqual(read, [
            {
                'id': self.course.id,
                'reference': False,
                'm2o_reference_id': False,
                'm2o_reference_model': False,
            }
        ])

    def test_properties(self):
        """Check that the display name of the relational properties are always loaded."""
        discussion = self.env['test_new_api.discussion'].create({
            'name': 'Test Discussion',
            'attributes_definition': [{
                'name': 'discussion_color_code',
                'string': 'Color Code',
                'type': 'char',
                'default': 'blue',
            }, {
                'name': 'moderator_partner_id',
                'string': 'Partner',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
            }],
            'participants': [Command.link(self.env.user.id)],
        })
        partner = self.env['test_new_api.partner'].create({'name': 'Test Partner Properties'})
        message = self.env['test_new_api.message'].create({
            'name': 'Test Message',
            'discussion': discussion.id,
            'author': self.env.user.id,
            'attributes': {
                'discussion_color_code': 'Test',
                'moderator_partner_id': partner.id,
            },
        })
        values = message.web_read({'attributes': False})[0]['attributes']
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]['name'], 'discussion_color_code')
        self.assertEqual(values[1]['name'], 'moderator_partner_id')
        self.assertEqual(values[1]['value'], (partner.id, 'Test Partner Properties'))
