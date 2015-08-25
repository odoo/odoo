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

    def test_onchange(self):
        """ test the effect of onchange() """
        discussion = self.env.ref('test_new_api.discussion_0')
        BODY = "What a beautiful day!"
        USER = self.env.user

        field_onchange = self.Message._onchange_spec()
        self.assertEqual(field_onchange.get('author'), '1')
        self.assertEqual(field_onchange.get('body'), '1')
        self.assertEqual(field_onchange.get('discussion'), '1')

        # changing 'discussion' should recompute 'name'
        values = {
            'discussion': discussion.id,
            'name': "[%s] %s" % ('', USER.name),
            'body': False,
            'author': USER.id,
            'size': 0,
        }
        self.env.invalidate_all()
        result = self.Message.onchange(values, 'discussion', field_onchange)
        self.assertIn('name', result['value'])
        self.assertEqual(result['value']['name'], "[%s] %s" % (discussion.name, USER.name))

        # changing 'body' should recompute 'size'
        values = {
            'discussion': discussion.id,
            'name': "[%s] %s" % (discussion.name, USER.name),
            'body': BODY,
            'author': USER.id,
            'size': 0,
        }
        self.env.invalidate_all()
        result = self.Message.onchange(values, 'body', field_onchange)
        self.assertIn('size', result['value'])
        self.assertEqual(result['value']['size'], len(BODY))

        # changing 'body' should not recompute 'name', even if 'discussion' and
        # 'name' are not consistent with each other
        values = {
            'discussion': discussion.id,
            'name': False,
            'body': BODY,
            'author': USER.id,
            'size': 0,
        }
        self.env.invalidate_all()
        result = self.Message.onchange(values, 'body', field_onchange)
        self.assertNotIn('name', result['value'])

    def test_onchange_one2many(self):
        """ test the effect of onchange() on one2many fields """
        BODY = "What a beautiful day!"
        USER = self.env.user

        # create an independent message
        message = self.Message.create({'body': BODY})
        self.assertEqual(message.name, "[%s] %s" % ('', USER.name))

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('name'), '1')
        self.assertEqual(field_onchange.get('messages'), '1')
        self.assertItemsEqual(
            [name for name in field_onchange if name.startswith('messages.')],
            ['messages.author', 'messages.body', 'messages.name', 'messages.size'],
        )

        # modify discussion name
        values = {
            'name': "Foo",
            'categories': [],
            'moderator': False,
            'participants': [],
            'messages': [
                (4, message.id),
                (0, 0, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': BODY,
                    'author': USER.id,
                    'size': len(BODY),
                }),
            ],
        }
        self.env.invalidate_all()
        result = self.Discussion.onchange(values, 'name', field_onchange)
        self.assertIn('messages', result['value'])
        self.assertEqual(result['value']['messages'], [
            (5,),
            (1, message.id, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': message.body,
                'author': message.author.name_get()[0],
                'size': message.size,
            }),
            (0, 0, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': BODY,
                'author': USER.name_get()[0],
                'size': len(BODY),
            }),
        ])

    def test_onchange_specific(self):
        """ test the effect of field-specific onchange method """
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.env.ref('base.user_demo')

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('moderator'), '1')
        self.assertFalse(any(name.startswith('participants.') for name in field_onchange))

        # first remove demo user from participants
        discussion.participants -= demo
        self.assertNotIn(demo, discussion.participants)

        # check that demo_user is added to participants when set as moderator
        values = {
            'name': discussion.name,
            'moderator': demo.id,
            'categories': [(4, cat.id) for cat in discussion.categories],
            'messages': [(4, msg.id) for msg in discussion.messages],
            'participants': [(4, usr.id) for usr in discussion.participants],
        }
        self.env.invalidate_all()
        result = discussion.onchange(values, 'moderator', field_onchange)

        self.assertIn('participants', result['value'])
        self.assertEqual(
            result['value']['participants'],
            [(5,)] + [(4, usr.id) for usr in discussion.participants + demo],
        )

    def test_onchange_one2many_value(self):
        """ test the value of the one2many field inside the onchange """
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.env.ref('base.user_demo')

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('messages'), '1')

        self.assertEqual(len(discussion.messages), 3)
        messages = [(4, msg.id) for msg in discussion.messages]
        messages[0] = (1, messages[0][1], {'body': 'test onchange'})
        values = {
            'name': discussion.name,
            'moderator': demo.id,
            'categories': [(4, cat.id) for cat in discussion.categories],
            'messages': messages,
            'participants': [(4, usr.id) for usr in discussion.participants],
            'message_concat': False,
        }
        result = discussion.onchange(values, 'messages', field_onchange)
        self.assertIn('message_concat', result['value'])
        self.assertEqual(result['value']['message_concat'],
                         "\n".join(["%s:%s" % (m.name, m.body) for m in discussion.messages]))
