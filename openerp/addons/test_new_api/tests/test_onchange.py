# -*- coding: utf-8 -*-

from openerp.tests import common

class TestOnChange(common.TransactionCase):

    def setUp(self):
        super(TestOnChange, self).setUp()
        self.Discussion = self.env['test_new_api.discussion']
        self.Message = self.env['test_new_api.message']

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
        discussion = self.env.ref('test_new_api.discussion_0')
        BODY = "What a beautiful day!"
        USER = self.env.user

        self.env.invalidate_all()
        result = self.Message.onchange({
            'discussion': discussion.id,
            'name': "[%s] %s" % ('', USER.name),
            'body': False,
            'author': USER.id,
            'size': 0,
        }, 'discussion')
        self.assertEqual(result['value'], {
            'name': "[%s] %s" % (discussion.name, USER.name),
        })

        self.env.invalidate_all()
        result = self.Message.onchange({
            'discussion': discussion.id,
            'name': "[%s] %s" % (discussion.name, USER.name),
            'body': BODY,
            'author': USER.id,
            'size': 0,
        }, 'body')
        self.assertEqual(result['value'], {
            'size': len(BODY),
        })

    def test_new_onchange_one2many(self):
        """ test the effect of onchange() on one2many fields """
        tocheck = ['messages.name', 'messages.body', 'messages.author', 'messages.size']
        BODY = "What a beautiful day!"
        USER = self.env.user

        # create an independent message
        message = self.Message.create({'body': BODY})
        self.assertEqual(message.name, "[%s] %s" % ('', USER.name))

        # modify messages
        self.env.invalidate_all()
        result = self.Discussion.onchange({
            'name': "Foo",
            'categories': [],
            'moderator': False,
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
        }, 'messages', tocheck)
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

        # modify discussion name
        self.env.invalidate_all()
        result = self.Discussion.onchange({
            'name': "Foo",
            'categories': [],
            'moderator': False,
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
        }, 'name', tocheck)
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

    def test_new_onchange_specific(self):
        """ test the effect of field-specific onchange method """
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.env.ref('base.user_demo')

        # first remove demo user from participants
        discussion.participants -= demo
        self.assertNotIn(demo, discussion.participants)

        # check that demo_user is added to participants when set as moderator
        name = discussion.name
        categories = [(4, cat.id) for cat in discussion.categories]
        participants = [(4, usr.id) for usr in discussion.participants]
        messages = [(4, msg.id) for msg in discussion.messages]

        self.env.invalidate_all()
        result = discussion.onchange({
            'name': name,
            'categories': categories,
            'moderator': demo.id,
            'participants': participants,
            'messages': messages,
        }, 'moderator')

        self.assertItemsEqual(list(result['value']), ['participants'])
        self.assertItemsEqual(result['value']['participants'], participants + [(4, demo.id)])
