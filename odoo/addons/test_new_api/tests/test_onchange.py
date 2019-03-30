# -*- coding: utf-8 -*-
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from odoo.tests import common

def strip_prefix(prefix, names):
    size = len(prefix)
    return [name[size:] for name in names if name.startswith(prefix)]

class TestOnChange(common.TransactionCase):

    def setUp(self):
        super(TestOnChange, self).setUp()
        self.Discussion = self.env['test_new_api.discussion']
        self.Message = self.env['test_new_api.message']
        self.EmailMessage = self.env['test_new_api.emailmessage']

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
        self.env.cache.invalidate()
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
        self.env.cache.invalidate()
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
        self.env.cache.invalidate()
        result = self.Message.onchange(values, 'body', field_onchange)
        self.assertNotIn('name', result['value'])

    def test_onchange_many2one(self):
        Category = self.env['test_new_api.category']

        field_onchange = Category._onchange_spec()
        self.assertEqual(field_onchange.get('parent'), '1')

        root = Category.create(dict(name='root'))

        values = {
            'name': 'test',
            'parent': root.id,
            'root_categ': False,
        }

        self.env.cache.invalidate()
        result = Category.onchange(values, 'parent', field_onchange).get('value', {})
        self.assertIn('root_categ', result)
        self.assertEqual(result['root_categ'], root.name_get()[0])

        values.update(result)
        values['parent'] = False

        self.env.cache.invalidate()
        result = Category.onchange(values, 'parent', field_onchange).get('value', {})
        self.assertIn('root_categ', result)
        self.assertIs(result['root_categ'], False)

    def test_onchange_one2many(self):
        """ test the effect of onchange() on one2many fields """
        USER = self.env.user

        # create an independent message
        message1 = self.Message.create({'body': "ABC"})
        message2 = self.Message.create({'body': "ABC"})
        self.assertEqual(message1.name, "[%s] %s" % ('', USER.name))

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('name'), '1')
        self.assertEqual(field_onchange.get('messages'), '1')
        self.assertItemsEqual(
            strip_prefix('messages.', field_onchange),
            ['author', 'body', 'name', 'size', 'important'],
        )

        # modify discussion name
        values = {
            'name': "Foo",
            'categories': [],
            'moderator': False,
            'participants': [],
            'messages': [
                (4, message1.id),
                (4, message2.id),
                (1, message2.id, {'body': "XYZ"}),
                (0, 0, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': "ABC",
                    'author': USER.id,
                    'size': 3,
                    'important': False,
                }),
            ],
        }
        self.env.cache.invalidate()
        result = self.Discussion.onchange(values, 'name', field_onchange)
        self.assertIn('messages', result['value'])
        self.assertEqual(result['value']['messages'], [
            (5,),
            (1, message1.id, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': "ABC",
                'author': USER.name_get()[0],
                'size': 3,
                'important': False,
            }),
            (1, message2.id, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': "XYZ",          # this must be sent back
                'author': USER.name_get()[0],
                'size': 3,
                'important': False,
            }),
            (0, 0, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': "ABC",
                'author': USER.name_get()[0],
                'size': 3,
                'important': False,
            }),
        ])

        # ensure onchange changing one2many without subfield works
        one_level_fields = {k: v for k, v in field_onchange.items() if k.count('.') < 1}
        values = dict(values, name='{generate_dummy_message}')
        result = self.Discussion.with_context(generate_dummy_message=True).onchange(values, 'name', one_level_fields)
        self.assertEqual(result['value']['messages'], [
            (5,),
            (4, message1.id),
            (4, message2.id),
            (0, 0, {}),
            (0, 0, {}),
        ])

    def test_onchange_one2many_reference(self):
        """ test the effect of onchange() on one2many fields with line references """
        BODY = "What a beautiful day!"
        USER = self.env.user
        REFERENCE = "virtualid42"

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('name'), '1')
        self.assertEqual(field_onchange.get('messages'), '1')
        self.assertItemsEqual(
            strip_prefix('messages.', field_onchange),
            ['author', 'body', 'name', 'size', 'important'],
        )

        # modify discussion name, and check that the reference of the new line
        # is returned
        values = {
            'name': "Foo",
            'categories': [],
            'moderator': False,
            'participants': [],
            'messages': [
                (0, REFERENCE, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': BODY,
                    'author': USER.id,
                    'size': len(BODY),
                    'important': False,
                }),
            ],
        }
        self.env.cache.invalidate()
        result = self.Discussion.onchange(values, 'name', field_onchange)
        self.assertIn('messages', result['value'])
        self.assertItemsEqual(result['value']['messages'], [
            (5,),
            (0, REFERENCE, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': BODY,
                'author': USER.name_get()[0],
                'size': len(BODY),
                'important': False,
            }),
        ])

    def test_onchange_one2many_multi(self):
        """ test the effect of multiple onchange methods on one2many fields """
        partner1 = self.env.ref('base.res_partner_1')
        multi = self.env['test_new_api.multi'].create({'partner': partner1.id})
        line1 = multi.lines.create({'multi': multi.id})

        field_onchange = multi._onchange_spec()
        self.assertEqual(field_onchange, {
            'name': '1',
            'partner': '1',
            'lines': None,
            'lines.name': None,
            'lines.partner': None,
            'lines.tags': None,
            'lines.tags.name': None,
        })

        values = multi._convert_to_write({key: multi[key] for key in ('name', 'partner', 'lines')})
        self.assertEqual(values, {
            'name': partner1.name,
            'partner': partner1.id,
            'lines': [(6, 0, [line1.id])],
        })

        # modify 'partner'
        #   -> set 'partner' on all lines
        #   -> recompute 'name'
        #       -> set 'name' on all lines
        partner2 = self.env.ref('base.res_partner_2')
        values = {
            'name': partner1.name,
            'partner': partner2.id,             # this one just changed
            'lines': [(6, 0, [line1.id]),
                      (0, 0, {'name': False, 'partner': False, 'tags': [(5,)]})],
        }
        self.env.cache.invalidate()

        result = multi.onchange(values, 'partner', field_onchange)
        self.assertEqual(result['value'], {
            'name': partner2.name,
            'lines': [
                (5,),
                (1, line1.id, {
                    'name': partner2.name,
                    'partner': (partner2.id, partner2.name),
                    'tags': [(5,)],
                }),
                (0, 0, {
                    'name': partner2.name,
                    'partner': (partner2.id, partner2.name),
                    'tags': [(5,)],
                }),
            ],
        })

        # do it again, but this time with a new tag on the second line
        values = {
            'name': partner1.name,
            'partner': partner2.id,             # this one just changed
            'lines': [(6, 0, [line1.id]),
                      (0, 0, {'name': False,
                              'partner': False,
                              'tags': [(5,), (0, 0, {'name': 'Tag'})]})],
        }
        self.env.cache.invalidate()

        result = multi.onchange(values, 'partner', field_onchange)
        expected_value = {
            'name': partner2.name,
            'lines': [
                (5,),
                # DLE P51: I see no visible change for this line, I don't really understand why it was the expected value.
                (4, line1.id),
                (0, 0, {
                    'name': partner2.name,
                    'partner': (partner2.id, partner2.name),
                    'tags': [(5,), (0, 0, {'name': 'Tag'})],
                }),
            ],
        }
        self.assertEqual(result['value'], expected_value)

        # ensure ID is not returned when asked and a many2many record is set to be created
        self.env.cache.invalidate()

        result = multi.onchange(values, 'partner', dict(field_onchange, **{'lines.tags.id': None}))
        self.assertEqual(result['value'], expected_value)

        # ensure inverse of one2many field is not returned
        self.env.cache.invalidate()

        result = multi.onchange(values, 'partner', dict(field_onchange, **{'lines.multi': None}))
        self.assertEqual(result['value'], expected_value)

    def test_onchange_specific(self):
        """ test the effect of field-specific onchange method """
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.env.ref('base.user_demo')

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('moderator'), '1')
        self.assertItemsEqual(
            strip_prefix('participants.', field_onchange),
            ['display_name'],
        )

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
        self.env.cache.invalidate()
        result = discussion.onchange(values, 'moderator', field_onchange)

        self.assertIn('participants', result['value'])
        self.assertItemsEqual(
            result['value']['participants'],
            [(5,)] + [(4, user.id) for user in discussion.participants + demo],
        )

    def test_onchange_default(self):
        """ test the effect of a conditional user-default on a field """
        Foo = self.env['test_new_api.foo']
        field_onchange = Foo._onchange_spec()
        self.assertTrue(Foo._fields['value1'].change_default)
        self.assertEqual(field_onchange.get('value1'), '1')

        # create a user-defined default based on 'value1'
        self.env['ir.default'].set('test_new_api.foo', 'value2', 666, condition='value1=42')

        # setting 'value1' to 42 should trigger the change of 'value2'
        self.env.cache.invalidate()
        values = {'name': 'X', 'value1': 42, 'value2': False}
        result = Foo.onchange(values, 'value1', field_onchange)
        self.assertEqual(result['value'], {'value2': 666})

        # setting 'value1' to 24 should not trigger the change of 'value2'
        self.env.cache.invalidate()
        values = {'name': 'X', 'value1': 24, 'value2': False}
        result = Foo.onchange(values, 'value1', field_onchange)
        self.assertEqual(result['value'], {})

    def test_onchange_one2many_value(self):
        """ test the value of the one2many field inside the onchange """
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.env.ref('base.user_demo')

        field_onchange = self.Discussion._onchange_spec()
        self.assertEqual(field_onchange.get('messages'), '1')

        self.assertEqual(len(discussion.messages), 3)
        messages = [(4, msg.id) for msg in discussion.messages]
        messages[0] = (1, messages[0][1], {'body': 'test onchange'})
        lines = ["%s:%s" % (m.name, m.body) for m in discussion.messages]
        lines[0] = "%s:%s" % (discussion.messages[0].name, 'test onchange')
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
        self.assertEqual(result['value']['message_concat'], "\n".join(lines))

    def test_onchange_one2many_with_domain_on_related_field(self):
        """ test the value of the one2many field when defined with a domain on a related field"""
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.env.ref('base.user_demo')

        # mimic UI behaviour, so we get subfields
        # (we need at least subfield: 'important_emails.important')
        view_info = self.Discussion.fields_view_get(
            view_id=self.env.ref('test_new_api.discussion_form').id,
            view_type='form')
        field_onchange = self.Discussion._onchange_spec(view_info=view_info)
        self.assertEqual(field_onchange.get('messages'), '1')

        BODY = "What a beautiful day!"
        USER = self.env.user

        # create standalone email
        email = self.EmailMessage.create({
            'discussion': discussion.id,
            'name': "[%s] %s" % ('', USER.name),
            'body': BODY,
            'author': USER.id,
            'important': False,
            'email_to': demo.email,
        })

        # check if server-side cache is working correctly
        self.env.cache.invalidate()
        self.assertIn(email, discussion.emails)
        self.assertNotIn(email, discussion.important_emails)
        email.important = True
        self.assertIn(email, discussion.important_emails)

        # check that when trigger an onchange, we don't reset important emails
        # (force `invalidate` as but appear in onchange only when we get a cache
        # miss)
        self.env.cache.invalidate()
        self.assertEqual(len(discussion.messages), 4)
        values = {
            'name': "Foo Bar",
            'moderator': demo.id,
            'categories': [(4, cat.id) for cat in discussion.categories],
            'messages': [(4, msg.id) for msg in discussion.messages],
            'participants': [(4, usr.id) for usr in discussion.participants],
            'important_messages': [(4, msg.id) for msg in discussion.important_messages],
            'important_emails': [(4, eml.id) for eml in discussion.important_emails],
        }
        self.env.cache.invalidate()
        result = discussion.onchange(values, 'name', field_onchange)

        self.assertEqual(
            result['value']['important_emails'],
            [(5,), (1, email.id, {
                'name': u'[Foo Bar] %s' % USER.name,
                'body': BODY,
                'author': USER.name_get()[0],
                'size': len(BODY),
                'important': True,
                'email_to': demo.email,
            })],
        )

    def test_onchange_related(self):
        value = {
            'message': 1,
            'message_name': False,
            'message_currency': 2,
        }
        field_onchange = {
            'message': '1',
            'message_name': None,
            'message_currency': None,
        }

        onchange_result = {
            'message_name': 'Hey dude!',
            'message_currency': self.env.user.name_get()[0],
        }

        self.env.cache.invalidate()
        Message = self.env['test_new_api.related']
        result = Message.onchange(value, ['message', 'message_name', 'message_currency'], field_onchange)

        self.assertEqual(result['value'], onchange_result)

        self.env.cache.invalidate()
        Message = self.env(user=self.env.ref('base.user_demo').id)['test_new_api.related']
        result = Message.onchange(value, ['message', 'message_name', 'message_currency'], field_onchange)

        self.assertEqual(result['value'], onchange_result)

    def test_onchange_many2one_one2many(self):
        """ Setting a many2one field should not read the inverse one2many. """
        discussion = self.env.ref('test_new_api.discussion_0')
        field_onchange = self.Message._onchange_spec()
        self.assertEqual(field_onchange.get('discussion'), '1')

        values = {
            'discussion': discussion.id,
            'name': "[%s] %s" % ('', self.env.user.name),
            'body': False,
            'author': self.env.uid,
            'size': 0,
        }

        called = [False]
        orig_read = type(discussion).read

        def mock_read(self, fields=None, load='_classic_read'):
            if discussion in self and 'messages' in (fields or ()):
                called[0] = True
            return orig_read(self, fields, load)

        # changing 'discussion' on message should not read 'messages' on discussion
        with patch.object(type(discussion), 'read', mock_read, create=True):
            self.env.cache.invalidate()
            self.Message.onchange(values, 'discussion', field_onchange)

        self.assertFalse(called[0], "discussion.messages has been read")
