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

        field_onchange = self.Message._onchange_spec()
        self.assertEqual(field_onchange.get('author'), '1')
        self.assertEqual(field_onchange.get('body'), '1')
        self.assertEqual(field_onchange.get('discussion'), '1')

        values = {
            'discussion': discussion.id,
            'name': "[%s] %s" % ('', USER.name),
            'body': False,
            'author': USER.id,
            'size': 0,
        }
        self.env.invalidate_all()
        result = self.Message.onchange(values, 'discussion', field_onchange)
        self.assertLessEqual(set(['name']), set(result['value']))
        self.assertEqual(result['value']['name'], "[%s] %s" % (discussion.name, USER.name))

        values = {
            'discussion': discussion.id,
            'name': "[%s] %s" % (discussion.name, USER.name),
            'body': BODY,
            'author': USER.id,
            'size': 0,
        }
        self.env.invalidate_all()
        result = self.Message.onchange(values, 'body', field_onchange)
        self.assertLessEqual(set(['size']), set(result['value']))
        self.assertEqual(result['value']['size'], len(BODY))

    def test_new_onchange_one2many(self):
        """ test the effect of onchange() on one2many fields """
        BODY = "What a beautiful day!"
        USER = self.env.user

        # create an independent message
        message = self.Message.create({'body': BODY})
        self.assertEqual(message.name, "[%s] %s" % ('', USER.name))

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('name'), '1')
        self.assertEqual(field_onchange.get('messages'), '1')

        # FIXME: commented out because currently not supported by the client
        # # modify messages
        # values = {
        #     'name': "Foo",
        #     'categories': [],
        #     'moderator': False,
        #     'participants': [],
        #     'messages': [
        #         (0, 0, {
        #             'name': "[%s] %s" % ('', USER.name),
        #             'body': BODY,
        #             'author': USER.id,
        #             'size': len(BODY),
        #         }),
        #         (4, message.id),
        #     ],
        # }
        # self.env.invalidate_all()
        # result = self.Discussion.onchange(values, 'messages', field_onchange)
        # self.assertLessEqual(set(['messages']), set(result['value']))
        # self.assertItemsEqual(result['value']['messages'], [
        #     (0, 0, {
        #         'name': "[%s] %s" % ("Foo", USER.name),
        #         'body': BODY,
        #         'author': USER.id,
        #         'size': len(BODY),
        #     }),
        #     (1, message.id, {
        #         'name': "[%s] %s" % ("Foo", USER.name),
        #         'body': BODY,
        #         'author': USER.id,
        #         'size': len(BODY),
        #     }),
        # ])

        # modify discussion name
        values = {
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
        }
        self.env.invalidate_all()
        result = self.Discussion.onchange(values, 'name', field_onchange)
        self.assertLessEqual(set(['messages']), set(result['value']))
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

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('moderator'), '1')

        # first remove demo user from participants
        discussion.participants -= demo
        self.assertNotIn(demo, discussion.participants)

        # check that demo_user is added to participants when set as moderator
        participants = [(4, usr.id) for usr in discussion.participants]
        values = {
            'name': discussion.name,
            'moderator': demo.id,
            'categories': [(4, cat.id) for cat in discussion.categories],
            'messages': [(4, msg.id) for msg in discussion.messages],
            'participants': participants,
        }
        self.env.invalidate_all()
        result = discussion.onchange(values, 'moderator', field_onchange)

        self.assertLessEqual(set(['participants']), set(result['value']))
        self.assertItemsEqual(result['value']['participants'], participants + [(4, demo.id)])
