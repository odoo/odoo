# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
from odoo.tests import common, Form

def strip_prefix(prefix, names):
    size = len(prefix)
    return [name[size:] for name in names if name.startswith(prefix)]

class TestOnChange(SavepointCaseWithUserDemo):

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
        partner1 = self.env['res.partner'].create({'name': 'A partner'})
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
        partner2 = self.env['res.partner'].create({'name': 'A second partner'})
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
                (1, line1.id, {
                    'name': partner2.name,
                    'partner': (partner2.id, partner2.name),
                    'tags': [(5,)],
                }),
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
        demo = self.user_demo

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

    def test_onchange_one2many_first(self):
        partner = self.env['res.partner'].create({
            'name': 'X',
            'country_id': self.env.ref('base.be').id,
        })
        with common.Form(self.env['test_new_api.multi']) as form:
            form.partner = partner
            self.assertEqual(form.partner, partner)
            self.assertEqual(form.name, partner.name)
            with form.lines.new() as line:
                # the first onchange() must have computed partner
                self.assertEqual(line.partner, partner)

    def test_onchange_one2many_value(self):
        """ test the value of the one2many field inside the onchange """
        discussion = self.env.ref('test_new_api.discussion_0')
        demo = self.user_demo

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
        demo = self.user_demo

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
        result = Message.onchange(value, 'message', field_onchange)

        self.assertEqual(result['value'], onchange_result)

        self.env.cache.invalidate()
        Message = self.env(user=self.user_demo.id)['test_new_api.related']
        result = Message.onchange(value, 'message', field_onchange)

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


class TestComputeOnchange(common.TransactionCase):

    def test_create(self):
        model = self.env['test_new_api.compute.onchange']

        # compute 'bar' (readonly) and 'baz' (editable)
        record = model.create({'active': True})
        self.assertEqual(record.bar, "r")
        self.assertEqual(record.baz, "z")

        # compute 'bar' and 'baz'
        record = model.create({'active': True, 'foo': "foo"})
        self.assertEqual(record.bar, "foor")
        self.assertEqual(record.baz, "fooz")

        # compute 'bar' but not 'baz'
        record = model.create({'active': True, 'foo': "foo", 'bar': "bar", 'baz': "baz"})
        self.assertEqual(record.bar, "foor")
        self.assertEqual(record.baz, "baz")

        # compute 'bar' and 'baz', but do not change its value
        record = model.create({'active': False, 'foo': "foo"})
        self.assertEqual(record.bar, "foor")
        self.assertEqual(record.baz, False)

        # compute 'bar' but not 'baz'
        record = model.create({'active': False, 'foo': "foo", 'bar': "bar", 'baz': "baz"})
        self.assertEqual(record.bar, "foor")
        self.assertEqual(record.baz, "baz")

    def test_copy(self):
        Model = self.env['test_new_api.compute.onchange']

        # create tags
        tag_foo, tag_bar = self.env['test_new_api.multi.tag'].create([
            {'name': 'foo1'},
            {'name': 'bar1'},
        ])

        # compute 'bar' (readonly), 'baz', 'line_ids' and 'tag_ids' (editable)
        record = Model.create({'active': True, 'foo': "foo1"})
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "foo1z")
        self.assertEqual(record.line_ids.mapped('foo'), ['foo1'])
        self.assertEqual(record.tag_ids, tag_foo)

        # manually update 'baz' and 'lines' to test copy attribute
        record.write({
            'baz': "baz1",
            'line_ids': [(0, 0, {'foo': 'bar'})],
            'tag_ids': [(4, tag_bar.id)],
        })
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "baz1")
        self.assertEqual(record.line_ids.mapped('foo'), ['foo1', 'bar'])
        self.assertEqual(record.tag_ids, tag_foo + tag_bar)

        # copy the record, and check results
        copied = record.copy()
        self.assertEqual(copied.foo, "foo1 (copy)")   # copied and modified
        self.assertEqual(copied.bar, "foo1 (copy)r")  # computed
        self.assertEqual(copied.baz, "baz1")          # copied
        self.assertEqual(record.line_ids.mapped('foo'), ['foo1', 'bar'])  # copied
        self.assertEqual(record.tag_ids, tag_foo + tag_bar)  # copied

    def test_write(self):
        model = self.env['test_new_api.compute.onchange']
        record = model.create({'active': True, 'foo': "foo"})
        self.assertEqual(record.bar, "foor")
        self.assertEqual(record.baz, "fooz")

        # recompute 'bar' (readonly) and 'baz' (editable)
        record.write({'foo': "foo1"})
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "foo1z")

        # recompute 'bar' but not 'baz'
        record.write({'foo': "foo2", 'bar': "bar2", 'baz': "baz2"})
        self.assertEqual(record.bar, "foo2r")
        self.assertEqual(record.baz, "baz2")

        # recompute 'bar' and 'baz', but do not change its value
        record.write({'active': False, 'foo': "foo3"})
        self.assertEqual(record.bar, "foo3r")
        self.assertEqual(record.baz, "baz2")

        # recompute 'bar' but not 'baz'
        record.write({'active': False, 'foo': "foo4", 'bar': "bar4", 'baz': "baz4"})
        self.assertEqual(record.bar, "foo4r")
        self.assertEqual(record.baz, "baz4")

    def test_set(self):
        model = self.env['test_new_api.compute.onchange']
        record = model.create({'active': True, 'foo': "foo"})
        self.assertEqual(record.bar, "foor")
        self.assertEqual(record.baz, "fooz")

        # recompute 'bar' (readonly) and 'baz' (editable)
        record.foo = "foo1"
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "foo1z")

        # do not recompute 'baz'
        record.baz = "baz2"
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "baz2")

        # recompute 'baz', but do not change its value
        record.active = False
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "baz2")

        # recompute 'baz', but do not change its value
        record.foo = "foo3"
        self.assertEqual(record.bar, "foo3r")
        self.assertEqual(record.baz, "baz2")

        # do not recompute 'baz'
        record.baz = "baz4"
        self.assertEqual(record.bar, "foo3r")
        self.assertEqual(record.baz, "baz4")

    def test_set_new(self):
        model = self.env['test_new_api.compute.onchange']
        record = model.new({'active': True})
        self.assertEqual(record.bar, "r")
        self.assertEqual(record.baz, "z")

        # recompute 'bar' (readonly) and 'baz' (editable)
        record.foo = "foo1"
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "foo1z")

        # do not recompute 'baz'
        record.baz = "baz2"
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "baz2")

        # recompute 'baz', but do not change its value
        record.active = False
        self.assertEqual(record.bar, "foo1r")
        self.assertEqual(record.baz, "baz2")

        # recompute 'baz', but do not change its value
        record.foo = "foo3"
        self.assertEqual(record.bar, "foo3r")
        self.assertEqual(record.baz, "baz2")

        # do not recompute 'baz'
        record.baz = "baz4"
        self.assertEqual(record.bar, "foo3r")
        self.assertEqual(record.baz, "baz4")

    def test_onchange(self):
        # check computations of 'bar' (readonly) and 'baz' (editable)
        form = common.Form(self.env['test_new_api.compute.onchange'])
        self.assertEqual(form.bar, "r")
        self.assertEqual(form.baz, False)
        form.active = True
        self.assertEqual(form.bar, "r")
        self.assertEqual(form.baz, "z")
        form.foo = "foo1"
        self.assertEqual(form.bar, "foo1r")
        self.assertEqual(form.baz, "foo1z")
        form.baz = "baz2"
        self.assertEqual(form.bar, "foo1r")
        self.assertEqual(form.baz, "baz2")
        form.active = False
        self.assertEqual(form.bar, "foo1r")
        self.assertEqual(form.baz, "baz2")
        form.foo = "foo3"
        self.assertEqual(form.bar, "foo3r")
        self.assertEqual(form.baz, "baz2")
        form.active = True
        self.assertEqual(form.bar, "foo3r")
        self.assertEqual(form.baz, "foo3z")

        with form.line_ids.new() as line:
            # check computation of 'bar' (readonly)
            self.assertEqual(line.foo, False)
            self.assertEqual(line.bar, "r")
            line.foo = "foo"
            self.assertEqual(line.foo, "foo")
            self.assertEqual(line.bar, "foor")

        record = form.save()
        self.assertEqual(record.bar, "foo3r")
        self.assertEqual(record.baz, "foo3z")

        form = common.Form(record)
        self.assertEqual(form.bar, "foo3r")
        self.assertEqual(form.baz, "foo3z")
        form.foo = "foo4"
        self.assertEqual(form.bar, "foo4r")
        self.assertEqual(form.baz, "foo4z")
        form.baz = "baz5"
        self.assertEqual(form.bar, "foo4r")
        self.assertEqual(form.baz, "baz5")
        form.active = False
        self.assertEqual(form.bar, "foo4r")
        self.assertEqual(form.baz, "baz5")
        form.foo = "foo6"
        self.assertEqual(form.bar, "foo6r")
        self.assertEqual(form.baz, "baz5")

    def test_onchange_default(self):
        form = common.Form(self.env['test_new_api.compute.onchange'].with_context(
            default_active=True, default_foo="foo", default_baz="baz",
        ))
        # 'baz' is computed editable, so when given a default value it should
        # 'not be recomputed, even if a dependency also has a default value
        self.assertEqual(form.foo, "foo")
        self.assertEqual(form.bar, "foor")
        self.assertEqual(form.baz, "baz")

    def test_onchange_once(self):
        """ Modifies `foo` field which will trigger an onchange method and
        checks it was triggered only one time. """
        form = Form(self.env['test_new_api.compute.onchange'].with_context(default_foo="oof"))
        record = form.save()
        self.assertEqual(record.foo, "oof")
        self.assertEqual(record.count, 1, "value onchange must be called only one time")

    def test_onchange_one2many(self):
        record = self.env['test_new_api.model_parent_m2o'].create({
            'name': 'Family',
            'child_ids': [
                (0, 0, {'name': 'W', 'cost': 10}),
                (0, 0, {'name': 'X', 'cost': 10}),
                (0, 0, {'name': 'Y'}),
                (0, 0, {'name': 'Z'}),
            ],
        })
        record.flush()
        self.assertEqual(record.child_ids.mapped('name'), list('WXYZ'))
        self.assertEqual(record.cost, 22)

        # modifying a line should not recompute the cost on other lines
        with common.Form(record) as form:
            with form.child_ids.edit(1) as line:
                line.name = 'XXX'
            self.assertEqual(form.cost, 15)

            with form.child_ids.edit(1) as line:
                line.cost = 20
            self.assertEqual(form.cost, 32)

            with form.child_ids.edit(2) as line:
                line.cost = 30
            self.assertEqual(form.cost, 61)

    def test_onchange_editable_compute_one2many(self):
        # create a record with a computed editable field ('edit') on lines
        record = self.env['test_new_api.compute_editable'].create({'line_ids': [(0, 0, {'value': 7})]})
        record.flush()
        line = record.line_ids
        self.assertRecordValues(line, [{'value': 7, 'edit': 7, 'count': 0}])

        # retrieve the onchange spec for calling 'onchange'
        spec = Form(record)._view['onchange']

        # The onchange on 'line_ids' should increment 'count' and keep the value
        # of 'edit' (this field should not be recomputed), whatever the order of
        # the fields in the dictionary.  This ensures that the value set by the
        # user on a computed editable field on a line is not lost.
        line_ids = [
            (1, line.id, {'value': 8, 'edit': 9, 'count': 0}),
            (0, 0, {'value': 8, 'edit': 9, 'count': 0}),
        ]
        result = record.onchange({'line_ids': line_ids}, 'line_ids', spec)
        expected = {'value': {
            'line_ids': [
                (5,),
                (1, line.id, {'value': 8, 'edit': 9, 'count': 8}),
                (0, 0, {'value': 8, 'edit': 9, 'count': 8}),
            ],
        }}
        self.assertEqual(result, expected)

        # change dict order in lines, and try again
        line_ids = [
            (op, id_, dict(reversed(list(vals.items()))))
            for op, id_, vals in line_ids
        ]
        result = record.onchange({'line_ids': line_ids}, 'line_ids', spec)
        self.assertEqual(result, expected)

    def test_computed_editable_one2many_domain(self):
        """ Test a computed, editable one2many field with a domain. """
        record = self.env['test_new_api.one2many'].create({'name': 'foo'})
        self.assertRecordValues(record.line_ids, [
            {'name': 'foo', 'count': 1},
        ])

        # trigger recomputation by changing name
        record.name = 'bar'
        self.assertRecordValues(record.line_ids, [
            {'name': 'foo', 'count': 1},
            {'name': 'bar', 'count': 1},
        ])

        # manually adding a line should not trigger recomputation
        record.line_ids.create({'name': 'baz', 'container_id': record.id})
        self.assertRecordValues(record.line_ids, [
            {'name': 'foo', 'count': 1},
            {'name': 'bar', 'count': 1},
            {'name': 'baz', 'count': 1},
        ])

        # changing the field in the domain should not trigger recomputation...
        record.line_ids[-1].count = 2
        self.assertRecordValues(record.line_ids, [
            {'name': 'foo', 'count': 1},
            {'name': 'bar', 'count': 1},
            {'name': 'baz', 'count': 2},
        ])

        # ...and may show cache inconsistencies
        record.line_ids[-1].count = 0
        self.assertRecordValues(record.line_ids, [
            {'name': 'foo', 'count': 1},
            {'name': 'bar', 'count': 1},
            {'name': 'baz', 'count': 0},
        ])
        record.flush()
        record.invalidate_cache()
        self.assertRecordValues(record.line_ids, [
            {'name': 'foo', 'count': 1},
            {'name': 'bar', 'count': 1},
        ])
