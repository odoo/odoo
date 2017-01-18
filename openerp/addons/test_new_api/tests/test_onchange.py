# -*- coding: utf-8 -*-

from openerp.tests import common

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

        self.env.invalidate_all()
        result = Category.onchange(values, 'parent', field_onchange).get('value', {})
        self.assertIn('root_categ', result)
        self.assertEqual(result['root_categ'], root.name_get()[0])

        values.update(result)
        values['parent'] = False

        self.env.invalidate_all()
        result = Category.onchange(values, 'parent', field_onchange).get('value', {})
        self.assertIn('root_categ', result)
        self.assertIs(result['root_categ'], False)

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
                (4, message.id),
                (0, 0, {
                    'name': "[%s] %s" % ('', USER.name),
                    'body': BODY,
                    'author': USER.id,
                    'size': len(BODY),
                    'important': False,
                }),
            ],
        }
        self.env.invalidate_all()
        result = self.Discussion.onchange(values, 'name', field_onchange)
        self.assertIn('messages', result['value'])
        self.assertItemsEqual(result['value']['messages'], [
            (5,),
            (1, message.id, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': message.body,
                'author': message.author.name_get()[0],
                'size': message.size,
                'important': message.important,
            }),
            (0, 0, {
                'name': "[%s] %s" % ("Foo", USER.name),
                'body': BODY,
                'author': USER.name_get()[0],
                'size': len(BODY),
                'important': False,
            }),
        ])

    def test_onchange_one2many_multi(self):
        """ test the effect of multiple onchange methods on one2many fields """
        partner = self.env.ref('base.res_partner_1')
        multi = self.env['test_new_api.multi'].create({'partner': partner.id})
        line = multi.lines.create({'multi': multi.id})

        field_onchange = multi._onchange_spec()
        self.assertEqual(field_onchange, {
            'name': '1',
            'partner': '1',
            'lines': None,
            'lines.name': None,
            'lines.partner': None,
        })

        values = multi._convert_to_write({key: multi[key] for key in ('name', 'partner', 'lines')})
        self.assertEqual(values, {
            'name': partner.name,
            'partner': partner.id,
            'lines': [(6, 0, [line.id])],
        })

        # modify 'partner'
        #   -> set 'partner' on all lines
        #   -> recompute 'name'
        #       -> set 'name' on all lines
        partner = self.env.ref('base.res_partner_2')
        values['partner'] = partner.id
        values['lines'].append((0, 0, {'name': False, 'partner': False}))
        self.env.invalidate_all()
        result = multi.onchange(values, 'partner', field_onchange)
        self.assertEqual(result['value'], {
            'name': partner.name,
            'lines': [
                (5,),
                (1, line.id, {'name': partner.name, 'partner': (partner.id, partner.name)}),
                (0, 0, {'name': partner.name, 'partner': (partner.id, partner.name)}),
            ],
        })

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
        self.env.invalidate_all()
        result = discussion.onchange(values, 'moderator', field_onchange)

        self.assertIn('participants', result['value'])
        self.assertItemsEqual(
            result['value']['participants'],
            [(5,)] + [(1, user.id, {'display_name': user.display_name})
                      for user in discussion.participants + demo],
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
        self.env.invalidate_all()
        self.assertIn(email, discussion.emails)
        self.assertNotIn(email, discussion.important_emails)
        email.important = True
        self.assertIn(email, discussion.important_emails)

        # check that when trigger an onchange, we don't reset important emails
        # (force `invalidate_all` as but appear in onchange only when we get a
        # cache miss)
        self.env.invalidate_all()
        self.assertEqual(len(discussion.messages), 4)
        values = {
            'name': "Foo Bar",
            'moderator': demo.id,
            'categories': [(4, cat.id) for cat in discussion.categories],
            'messages': [(4, msg.id) for msg in discussion.messages],
            'participants': [(4, usr.id) for usr in discussion.participants],
            'message_changes': 0,
            'important_messages': [(4, msg.id) for msg in discussion.important_messages],
            'important_emails': [(4, eml.id) for eml in discussion.important_emails],
        }
        result = discussion.onchange(values, 'name', field_onchange)

        # When one2many domain contains non-computed field, things are ok
        self.assertEqual(result['value']['important_messages'],
                         [(5,)] + [(1, msg.id, {
                                    'name': msg.name,
                                    'body': msg.body,
                                    'author': (msg.author.id, msg.author.display_name),
                                    'size': msg.size
                                    }) for msg in discussion.important_messages])

        # But here with commit 5676d81, we get value of: [(2, email.id)]
        self.assertEqual(
            result['value']['important_emails'],
            [(5,),
             (1, email.id, {
                 'name': u'[Foo Bar] %s' % USER.name,
                 'body': email.body,
                 'author': USER.name_get()[0],
                 'important': True,
                 'email_to': demo.email,
                 'size': email.size,
             })]
        )
