# -*- coding: utf-8 -*-

from openerp import scope
from openerp.tests import common

class TestOnChange(common.TransactionCase):

    def setUp(self):
        super(TestOnChange, self).setUp()
        self.Discussion = self.registry('test_new_api.discussion')
        self.Message = self.registry('test_new_api.message')

    def test_default_get(self):
        """ checking values returned by default_get() """
        fields = ['name', 'categories', 'participants', 'messages']
        values = self.Discussion.default_get(fields)
        self.assertEqual(values, {})

    def test_get_field(self):
        """ checking that accessing an unknown attribute does nothing special """
        with self.assertRaises(AttributeError):
            self.Discussion.not_really_a_method()

    def test_new_onchange(self):
        """ test the effect of onchange() """
        discussion = scope.ref('test_new_api.discussion_0')
        BODY = "What a beautiful day!"
        USER = scope.user

        result = self.Message.onchange('discussion', {
            'discussion': discussion.id,
            'name': "[%s] %s" % ('', USER.name),
            'body': False,
            'author': USER.id,
            'size': 0,
        })
        self.assertEqual(result['value'], {
            'name': "[%s] %s" % (discussion.name, USER.name),
        })

        result = self.Message.onchange('body', {
            'discussion': discussion.id,
            'name': "[%s] %s" % (discussion.name, USER.name),
            'body': BODY,
            'author': USER.id,
            'size': 0,
        })
        self.assertEqual(result['value'], {
            'size': len(BODY),
        })

    def test_new_onchange_one2many(self):
        """ test the effect of onchange() on one2many fields """
        tocheck = ['messages.name', 'messages.body', 'messages.author', 'messages.size']
        BODY = "What a beautiful day!"
        USER = scope.user

        # create an independent message
        message = self.Message.create({'body': BODY})
        self.assertEqual(message.name, "[%s] %s" % ('', USER.name))

        # modify messages
        result = self.Discussion.onchange('messages', {
            'name': "Foo",
            'categories': [],
            'participants': [],
            'messages': [
                (0, 0, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': BODY,
                    'author': USER.id,
                    'size': len(BODY),
                }),
                (1, message.id, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': BODY,
                    'author': USER.id,
                    'size': len(BODY),
                }),
            ],
        }, tocheck)
        self.assertEqual(result['value'], {})

        # modify discussion name
        result = self.Discussion.onchange('name', {
            'name': "Foo",
            'categories': [],
            'participants': [],
            'messages': [
                (0, 0, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': BODY,
                    'author': USER.id,
                    'size': len(BODY),
                }),
                (4, message.id),
            ],
        }, tocheck)
        self.assertItemsEqual(list(result['value']), ['messages'])
        self.assertItemsEqual(result['value']['messages'], [
            (0, 0, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': BODY,
                'author': USER.id,
                'size': len(BODY),
            }),
            (1, message.id, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': BODY,
                'author': USER.id,
                'size': len(BODY),
            }),
        ])
