#
# test cases for new-style fields
#
from datetime import date, datetime

from odoo.exceptions import AccessError, except_orm
from odoo.tests import common
from odoo.tools import mute_logger


class TestFields(common.TransactionCase):

    def test_00_basics(self):
        """ test accessing new fields """
        # find a discussion
        discussion = self.env.ref('test_new_api.discussion_0')

        # read field as a record attribute or as a record item
        self.assertIsInstance(discussion.name, basestring)
        self.assertIsInstance(discussion['name'], basestring)
        self.assertEqual(discussion['name'], discussion.name)

        # read it with method read()
        values = discussion.read(['name'])[0]
        self.assertEqual(values['name'], discussion.name)

    def test_01_basic_get_assertion(self):
        """ test item getter """
        # field access works on single record
        record = self.env.ref('test_new_api.message_0_0')
        self.assertEqual(len(record), 1)
        ok = record.body

        # field access fails on multiple records
        records = self.env['test_new_api.message'].search([])
        assert len(records) > 1
        with self.assertRaises(ValueError):
            faulty = records.body

    def test_01_basic_set_assertion(self):
        """ test item setter """
        # field assignment works on single record
        record = self.env.ref('test_new_api.message_0_0')
        self.assertEqual(len(record), 1)
        record.body = 'OK'

        # field assignment fails on multiple records
        records = self.env['test_new_api.message'].search([])
        assert len(records) > 1
        with self.assertRaises(ValueError):
            records.body = 'Faulty'

    def test_10_computed(self):
        """ check definition of computed fields """
        # by default function fields are not stored and readonly
        field = self.env['test_new_api.message']._fields['size']
        self.assertFalse(field.store)
        self.assertTrue(field.readonly)

        field = self.env['test_new_api.message']._fields['name']
        self.assertTrue(field.store)
        self.assertTrue(field.readonly)

    def test_10_non_stored(self):
        """ test non-stored fields """
        # a field declared with store=False should not have a column
        field = self.env['test_new_api.category']._fields['dummy']
        self.assertFalse(field.store)
        self.assertFalse(field.compute)
        self.assertFalse(field.inverse)

        # find messages
        for message in self.env['test_new_api.message'].search([]):
            # check definition of field
            self.assertEqual(message.size, len(message.body or ''))

            # check recomputation after record is modified
            size = message.size
            message.write({'body': (message.body or '') + "!!!"})
            self.assertEqual(message.size, size + 3)

        # special case: computed field without dependency must be computed
        record = self.env['test_new_api.mixed'].create({})
        self.assertTrue(record.now)

    def test_11_stored(self):
        """ test stored fields """
        def check_stored(disc):
            """ Check the stored computed field on disc.messages """
            for msg in disc.messages:
                self.assertEqual(msg.name, "[%s] %s" % (disc.name, msg.author.name))

        # find the demo discussion, and check messages
        discussion1 = self.env.ref('test_new_api.discussion_0')
        self.assertTrue(discussion1.messages)
        check_stored(discussion1)

        # modify discussion name, and check again messages
        discussion1.name = 'Talking about stuff...'
        check_stored(discussion1)

        # switch message from discussion, and check again
        discussion2 = discussion1.copy({'name': 'Another discussion'})
        message2 = discussion1.messages[0]
        message2.discussion = discussion2
        check_stored(discussion2)

        # create a new discussion with messages, and check their name
        user_root = self.env.ref('base.user_root')
        user_demo = self.env.ref('base.user_demo')
        discussion3 = self.env['test_new_api.discussion'].create({
            'name': 'Stuff',
            'participants': [(4, user_root.id), (4, user_demo.id)],
            'messages': [
                (0, 0, {'author': user_root.id, 'body': 'one'}),
                (0, 0, {'author': user_demo.id, 'body': 'two'}),
                (0, 0, {'author': user_root.id, 'body': 'three'}),
            ],
        })
        check_stored(discussion3)

        # modify the discussion messages: edit the 2nd one, remove the last one
        # (keep modifications in that order, as they reproduce a former bug!)
        discussion3.write({
            'messages': [
                (4, discussion3.messages[0].id),
                (1, discussion3.messages[1].id, {'author': user_root.id}),
                (2, discussion3.messages[2].id),
            ],
        })
        check_stored(discussion3)

    def test_11_computed_access(self):
        """ test computed fields with access right errors """
        User = self.env['res.users']
        user1 = User.create({'name': 'Aaaah', 'login': 'a'})
        user2 = User.create({'name': 'Boooh', 'login': 'b'})
        user3 = User.create({'name': 'Crrrr', 'login': 'c'})
        # add a rule to not give access to user2
        self.env['ir.rule'].create({
            'model_id': self.env['ir.model'].search([('model', '=', 'res.users')]).id,
            'domain_force': "[('id', '!=', %d)]" % user2.id,
        })
        # group users as a recordset, and read them as user demo
        users = (user1 + user2 + user3).sudo(self.env.ref('base.user_demo'))
        user1, user2, user3 = users
        # regression test: a bug invalidated the field's value from cache
        user1.company_type
        with self.assertRaises(AccessError):
            user2.company_type
        user3.company_type

    def test_12_recursive(self):
        """ test recursively dependent fields """
        Category = self.env['test_new_api.category']
        abel = Category.create({'name': 'Abel'})
        beth = Category.create({'name': 'Bethany'})
        cath = Category.create({'name': 'Catherine'})
        dean = Category.create({'name': 'Dean'})
        ewan = Category.create({'name': 'Ewan'})
        finn = Category.create({'name': 'Finnley'})
        gabe = Category.create({'name': 'Gabriel'})

        cath.parent = finn.parent = gabe
        abel.parent = beth.parent = cath
        dean.parent = ewan.parent = finn

        self.assertEqual(abel.display_name, "Gabriel / Catherine / Abel")
        self.assertEqual(beth.display_name, "Gabriel / Catherine / Bethany")
        self.assertEqual(cath.display_name, "Gabriel / Catherine")
        self.assertEqual(dean.display_name, "Gabriel / Finnley / Dean")
        self.assertEqual(ewan.display_name, "Gabriel / Finnley / Ewan")
        self.assertEqual(finn.display_name, "Gabriel / Finnley")
        self.assertEqual(gabe.display_name, "Gabriel")

        ewan.parent = cath
        self.assertEqual(ewan.display_name, "Gabriel / Catherine / Ewan")

        cath.parent = finn
        self.assertEqual(ewan.display_name, "Gabriel / Finnley / Catherine / Ewan")

    def test_12_recursive_recompute(self):
        """ test recomputation on recursively dependent field """
        a = self.env['test_new_api.recursive'].create({'name': 'A'})
        b = self.env['test_new_api.recursive'].create({'name': 'B', 'parent': a.id})
        c = self.env['test_new_api.recursive'].create({'name': 'C', 'parent': b.id})
        d = self.env['test_new_api.recursive'].create({'name': 'D', 'parent': c.id})
        self.assertEqual(a.display_name, 'A')
        self.assertEqual(b.display_name, 'A / B')
        self.assertEqual(c.display_name, 'A / B / C')
        self.assertEqual(d.display_name, 'A / B / C / D')

        b.parent = False
        self.assertEqual(a.display_name, 'A')
        self.assertEqual(b.display_name, 'B')
        self.assertEqual(c.display_name, 'B / C')
        self.assertEqual(d.display_name, 'B / C / D')

        b.name = 'X'
        self.assertEqual(a.display_name, 'A')
        self.assertEqual(b.display_name, 'X')
        self.assertEqual(c.display_name, 'X / C')
        self.assertEqual(d.display_name, 'X / C / D')

    def test_12_cascade(self):
        """ test computed field depending on computed field """
        message = self.env.ref('test_new_api.message_0_0')
        message.invalidate_cache()
        double_size = message.double_size
        self.assertEqual(double_size, message.size)

    def test_13_inverse(self):
        """ test inverse computation of fields """
        Category = self.env['test_new_api.category']
        abel = Category.create({'name': 'Abel'})
        beth = Category.create({'name': 'Bethany'})
        cath = Category.create({'name': 'Catherine'})
        dean = Category.create({'name': 'Dean'})
        ewan = Category.create({'name': 'Ewan'})
        finn = Category.create({'name': 'Finnley'})
        gabe = Category.create({'name': 'Gabriel'})
        self.assertEqual(ewan.display_name, "Ewan")

        ewan.display_name = "Abel / Bethany / Catherine / Erwan"

        self.assertEqual(beth.parent, abel)
        self.assertEqual(cath.parent, beth)
        self.assertEqual(ewan.parent, cath)
        self.assertEqual(ewan.name, "Erwan")

        record = self.env['test_new_api.compute.inverse']

        # create/write on 'foo' should only invoke the compute method
        record.counts.update(compute=0, inverse=0)
        record = record.create({'foo': 'Hi'})
        self.assertEqual(record.foo, 'Hi')
        self.assertEqual(record.bar, 'Hi')
        self.assertEqual(record.counts, {'compute': 1, 'inverse': 0})

        record.counts.update(compute=0, inverse=0)
        record.write({'foo': 'Ho'})
        self.assertEqual(record.foo, 'Ho')
        self.assertEqual(record.bar, 'Ho')
        self.assertEqual(record.counts, {'compute': 1, 'inverse': 0})

        # create/write on 'bar' should only invoke the inverse method
        record.counts.update(compute=0, inverse=0)
        record = record.create({'bar': 'Hi'})
        self.assertEqual(record.foo, 'Hi')
        self.assertEqual(record.bar, 'Hi')
        self.assertEqual(record.counts, {'compute': 0, 'inverse': 1})

        record.counts.update(compute=0, inverse=0)
        record.write({'bar': 'Ho'})
        self.assertEqual(record.foo, 'Ho')
        self.assertEqual(record.bar, 'Ho')
        self.assertEqual(record.counts, {'compute': 0, 'inverse': 1})

    def test_14_search(self):
        """ test search on computed fields """
        discussion = self.env.ref('test_new_api.discussion_0')

        # determine message sizes
        sizes = set(message.size for message in discussion.messages)

        # search for messages based on their size
        for size in sizes:
            messages0 = self.env['test_new_api.message'].search(
                [('discussion', '=', discussion.id), ('size', '<=', size)])

            messages1 = self.env['test_new_api.message'].browse()
            for message in discussion.messages:
                if message.size <= size:
                    messages1 += message

            self.assertEqual(messages0, messages1)

    def test_15_constraint(self):
        """ test new-style Python constraints """
        discussion = self.env.ref('test_new_api.discussion_0')

        # remove oneself from discussion participants: we can no longer create
        # messages in discussion
        discussion.participants -= self.env.user
        with self.assertRaises(Exception):
            self.env['test_new_api.message'].create({'discussion': discussion.id, 'body': 'Whatever'})

        # make sure that assertRaises() does not leave fields to recompute
        self.assertFalse(self.env.has_todo())

        # put back oneself into discussion participants: now we can create
        # messages in discussion
        discussion.participants += self.env.user
        self.env['test_new_api.message'].create({'discussion': discussion.id, 'body': 'Whatever'})

    def test_20_float(self):
        """ test float fields """
        record = self.env['test_new_api.mixed'].create({})

        # assign value, and expect rounding
        record.write({'number': 2.4999999999999996})
        self.assertEqual(record.number, 2.50)

        # same with field setter
        record.number = 2.4999999999999996
        self.assertEqual(record.number, 2.50)

    def test_20_monetary(self):
        """ test monetary fields """
        record = self.env['test_new_api.mixed'].create({})
        self.assertTrue(record.currency_id)
        self.assertEqual(record.currency_id.rounding, 0.01)

        # the conversion to cache should round the value to 14.700000000000001
        record.amount = 14.7
        self.assertNotEqual(record.amount, 14.7)
        self.assertEqual(record.amount, 14.700000000000001)

        # however when stored to database, it should be serialized as 14.70
        self.cr.execute('SELECT amount FROM test_new_api_mixed WHERE id=%s', (record.id,))
        (amount,) = self.cr.fetchone()
        self.assertEqual(amount, 14.7)

    def test_21_date(self):
        """ test date fields """
        record = self.env['test_new_api.mixed'].create({})

        # one may assign False or None
        record.date = None
        self.assertFalse(record.date)

        # one may assign date and datetime objects
        record.date = date(2012, 5, 1)
        self.assertEqual(record.date, '2012-05-01')

        record.date = datetime(2012, 5, 1, 10, 45, 00)
        self.assertEqual(record.date, '2012-05-01')

        # one may assign dates in the default format, and it must be checked
        record.date = '2012-05-01'
        self.assertEqual(record.date, '2012-05-01')

        with self.assertRaises(ValueError):
            record.date = '12-5-1'

    def test_22_selection(self):
        """ test selection fields """
        record = self.env['test_new_api.mixed'].create({})

        # one may assign False or None
        record.lang = None
        self.assertFalse(record.lang)

        # one may assign a value, and it must be checked
        for language in self.env['res.lang'].search([]):
            record.lang = language.code
        with self.assertRaises(ValueError):
            record.lang = 'zz_ZZ'

    def test_23_relation(self):
        """ test relation fields """
        demo = self.env.ref('base.user_demo')
        message = self.env.ref('test_new_api.message_0_0')

        # check environment of record and related records
        self.assertEqual(message.env, self.env)
        self.assertEqual(message.discussion.env, self.env)

        demo_env = self.env(user=demo)
        self.assertNotEqual(demo_env, self.env)

        # check environment of record and related records
        self.assertEqual(message.env, self.env)
        self.assertEqual(message.discussion.env, self.env)

        # "migrate" message into demo_env, and check again
        demo_message = message.sudo(demo)
        self.assertEqual(demo_message.env, demo_env)
        self.assertEqual(demo_message.discussion.env, demo_env)

        # assign record's parent to a record in demo_env
        message.discussion = message.discussion.copy({'name': 'Copy'})

        # both message and its parent field must be in self.env
        self.assertEqual(message.env, self.env)
        self.assertEqual(message.discussion.env, self.env)

    def test_24_reference(self):
        """ test reference fields. """
        record = self.env['test_new_api.mixed'].create({})

        # one may assign False or None
        record.reference = None
        self.assertFalse(record.reference)

        # one may assign a user or a partner...
        record.reference = self.env.user
        self.assertEqual(record.reference, self.env.user)
        record.reference = self.env.user.partner_id
        self.assertEqual(record.reference, self.env.user.partner_id)
        # ... but no record from a model that starts with 'ir.'
        with self.assertRaises(ValueError):
            record.reference = self.env['ir.model'].search([], limit=1)

    def test_25_related(self):
        """ test related fields. """
        message = self.env.ref('test_new_api.message_0_0')
        discussion = message.discussion

        # by default related fields are not stored
        field = message._fields['discussion_name']
        self.assertFalse(field.store)
        self.assertFalse(field.readonly)

        # check value of related field
        self.assertEqual(message.discussion_name, discussion.name)

        # change discussion name, and check result
        discussion.name = 'Foo'
        self.assertEqual(message.discussion_name, 'Foo')

        # change discussion name via related field, and check result
        message.discussion_name = 'Bar'
        self.assertEqual(discussion.name, 'Bar')
        self.assertEqual(message.discussion_name, 'Bar')

        # change discussion name via related field on several records
        discussion1 = discussion.create({'name': 'X1'})
        discussion2 = discussion.create({'name': 'X2'})
        discussion1.participants = discussion2.participants = self.env.user
        message1 = message.create({'discussion': discussion1.id})
        message2 = message.create({'discussion': discussion2.id})
        self.assertEqual(message1.discussion_name, 'X1')
        self.assertEqual(message2.discussion_name, 'X2')

        (message1 + message2).write({'discussion_name': 'X3'})
        self.assertEqual(discussion1.name, 'X3')
        self.assertEqual(discussion2.name, 'X3')

        # search on related field, and check result
        search_on_related = self.env['test_new_api.message'].search([('discussion_name', '=', 'Bar')])
        search_on_regular = self.env['test_new_api.message'].search([('discussion.name', '=', 'Bar')])
        self.assertEqual(search_on_related, search_on_regular)

        # check that field attributes are copied
        message_field = message.fields_get(['discussion_name'])['discussion_name']
        discussion_field = discussion.fields_get(['name'])['name']
        self.assertEqual(message_field['help'], discussion_field['help'])

    def test_25_related_single(self):
        """ test related fields with a single field in the path. """
        record = self.env['test_new_api.related'].create({'name': 'A'})
        self.assertEqual(record.related_name, record.name)
        self.assertEqual(record.related_related_name, record.name)

        # check searching on related fields
        records0 = record.search([('name', '=', 'A')])
        self.assertIn(record, records0)
        records1 = record.search([('related_name', '=', 'A')])
        self.assertEqual(records1, records0)
        records2 = record.search([('related_related_name', '=', 'A')])
        self.assertEqual(records2, records0)

        # check writing on related fields
        record.write({'related_name': 'B'})
        self.assertEqual(record.name, 'B')
        record.write({'related_related_name': 'C'})
        self.assertEqual(record.name, 'C')

    def test_25_related_multi(self):
        """ test write() on several related fields based on a common computed field. """
        foo = self.env['test_new_api.foo'].create({'name': 'A', 'value1': 1, 'value2': 2})
        bar = self.env['test_new_api.bar'].create({'name': 'A'})
        self.assertEqual(bar.foo, foo)
        self.assertEqual(bar.value1, 1)
        self.assertEqual(bar.value2, 2)

        foo.invalidate_cache()
        bar.write({'value1': 3, 'value2': 4})
        self.assertEqual(foo.value1, 3)
        self.assertEqual(foo.value2, 4)

    def test_26_inherited(self):
        """ test inherited fields. """
        # a bunch of fields are inherited from res_partner
        for user in self.env['res.users'].search([]):
            partner = user.partner_id
            for field in ('is_company', 'name', 'email', 'country_id'):
                self.assertEqual(getattr(user, field), getattr(partner, field))
                self.assertEqual(user[field], partner[field])

    def test_27_company_dependent(self):
        """ test company-dependent fields. """
        # consider three companies
        company0 = self.env.ref('base.main_company')
        company1 = self.env['res.company'].create({'name': 'A', 'parent_id': company0.id})
        company2 = self.env['res.company'].create({'name': 'B', 'parent_id': company1.id})
        # create one user per company
        user0 = self.env['res.users'].create({'name': 'Foo', 'login': 'foo',
                                              'company_id': company0.id, 'company_ids': []})
        user1 = self.env['res.users'].create({'name': 'Bar', 'login': 'bar',
                                              'company_id': company1.id, 'company_ids': []})
        user2 = self.env['res.users'].create({'name': 'Baz', 'login': 'baz',
                                              'company_id': company2.id, 'company_ids': []})
        # create a default value for the company-dependent field
        field = self.env['ir.model.fields'].search([('model', '=', 'test_new_api.company'),
                                                    ('name', '=', 'foo')])
        self.env['ir.property'].create({'name': 'foo', 'fields_id': field.id,
                                        'value': 'default', 'type': 'char'})

        # create/modify a record, and check the value for each user
        record = self.env['test_new_api.company'].create({'foo': 'main'})
        record.invalidate_cache()
        self.assertEqual(record.sudo(user0).foo, 'main')
        self.assertEqual(record.sudo(user1).foo, 'default')
        self.assertEqual(record.sudo(user2).foo, 'default')

        record.sudo(user1).foo = 'alpha'
        record.invalidate_cache()
        self.assertEqual(record.sudo(user0).foo, 'main')
        self.assertEqual(record.sudo(user1).foo, 'alpha')
        self.assertEqual(record.sudo(user2).foo, 'default')

        # create company record and attribute
        company_record = self.env['test_new_api.company'].create({'foo': 'ABC'})
        attribute_record = self.env['test_new_api.company.attr'].create({
            'company': company_record.id,
            'quantity': 1,
        })
        self.assertEqual(attribute_record.bar, 'ABC')

        # change quantity, 'bar' should recompute to 'ABCABC'
        attribute_record.quantity = 2
        self.assertEqual(attribute_record.bar, 'ABCABC')
        self.assertFalse(self.env.has_todo())

        # change company field 'foo', 'bar' should recompute to 'DEFDEF'
        company_record.foo = 'DEF'
        self.assertEqual(attribute_record.company.foo, 'DEF')
        self.assertEqual(attribute_record.bar, 'DEFDEF')
        self.assertFalse(self.env.has_todo())

    def test_30_read(self):
        """ test computed fields as returned by read(). """
        discussion = self.env.ref('test_new_api.discussion_0')

        for message in discussion.messages:
            display_name = message.display_name
            size = message.size

            data = message.read(['display_name', 'size'])[0]
            self.assertEqual(data['display_name'], display_name)
            self.assertEqual(data['size'], size)

    def test_31_prefetch(self):
        """ test prefetch of records handle AccessError """
        Category = self.env['test_new_api.category']
        cat1 = Category.create({'name': 'NOACCESS'})
        cat2 = Category.create({'name': 'ACCESS', 'parent': cat1.id})
        cats = cat1 + cat2

        self.env.clear()

        cat1, cat2 = cats
        self.assertEqual(cat2.name, 'ACCESS')
        # both categories should be ready for prefetching
        self.assertItemsEqual(cat2._prefetch[Category._name], cats.ids)
        # but due to our (lame) overwrite of `read`, it should not forbid us to read records we have access to
        self.assertFalse(cat2.discussions)
        self.assertEqual(cat2.parent, cat1)
        with self.assertRaises(AccessError):
            cat1.name

    def test_40_new(self):
        """ test new records. """
        discussion = self.env.ref('test_new_api.discussion_0')

        # create a new message
        message = self.env['test_new_api.message'].new()
        self.assertFalse(message.id)

        # assign some fields; should have no side effect
        message.discussion = discussion
        message.body = BODY = "May the Force be with you."
        self.assertEqual(message.discussion, discussion)
        self.assertEqual(message.body, BODY)
        self.assertFalse(message.author)
        self.assertNotIn(message, discussion.messages)

        # check computed values of fields
        self.assertEqual(message.name, "[%s] %s" % (discussion.name, ''))
        self.assertEqual(message.size, len(BODY))

    @mute_logger('odoo.addons.base.ir.ir_model')
    def test_41_new_related(self):
        """ test the behavior of related fields starting on new records. """
        # make discussions unreadable for demo user
        access = self.env.ref('test_new_api.access_discussion')
        access.write({'perm_read': False})

        # create an environment for demo user
        env = self.env(user=self.env.ref('base.user_demo'))
        self.assertEqual(env.user.login, "demo")

        # create a new message as demo user
        discussion = self.env.ref('test_new_api.discussion_0')
        message = env['test_new_api.message'].new({'discussion': discussion})
        self.assertEqual(message.discussion, discussion)

        # read the related field discussion_name
        self.assertEqual(message.discussion.env, env)
        self.assertEqual(message.discussion_name, discussion.name)
        with self.assertRaises(AccessError):
            message.discussion.name

    @mute_logger('odoo.addons.base.ir.ir_model')
    def test_42_new_related(self):
        """ test the behavior of related fields traversing new records. """
        # make discussions unreadable for demo user
        access = self.env.ref('test_new_api.access_discussion')
        access.write({'perm_read': False})

        # create an environment for demo user
        env = self.env(user=self.env.ref('base.user_demo'))
        self.assertEqual(env.user.login, "demo")

        # create a new discussion and a new message as demo user
        discussion = env['test_new_api.discussion'].new({'name': 'Stuff'})
        message = env['test_new_api.message'].new({'discussion': discussion})
        self.assertEqual(message.discussion, discussion)

        # read the related field discussion_name
        self.assertNotEqual(message.sudo().env, message.env)
        self.assertEqual(message.discussion_name, discussion.name)

    def test_50_defaults(self):
        """ test default values. """
        fields = ['discussion', 'body', 'author', 'size']
        defaults = self.env['test_new_api.message'].default_get(fields)
        self.assertEqual(defaults, {'author': self.env.uid})

        defaults = self.env['test_new_api.mixed'].default_get(['number'])
        self.assertEqual(defaults, {'number': 3.14})

    def test_50_search_many2one(self):
        """ test search through a path of computed fields"""
        messages = self.env['test_new_api.message'].search(
            [('author_partner.name', '=', 'Demo User')])
        self.assertEqual(messages, self.env.ref('test_new_api.message_0_1'))

    def test_60_x2many_domain(self):
        """ test the cache consistency of a x2many field with a domain """
        discussion = self.env.ref('test_new_api.discussion_0')
        message = discussion.messages[0]
        self.assertNotIn(message, discussion.important_messages)

        message.important = True
        self.assertIn(message, discussion.important_messages)

        # writing on very_important_messages should call its domain method
        self.assertIn(message, discussion.very_important_messages)
        discussion.write({'very_important_messages': [(5,)]})
        self.assertFalse(discussion.very_important_messages)
        self.assertFalse(message.exists())


class TestHtmlField(common.TransactionCase):

    def setUp(self):
        super(TestHtmlField, self).setUp()
        self.model = self.env['test_new_api.mixed']

    def test_00_sanitize(self):
        self.assertEqual(self.model._fields['comment1'].sanitize, False)
        self.assertEqual(self.model._fields['comment2'].sanitize_attributes, True)
        self.assertEqual(self.model._fields['comment2'].strip_classes, False)
        self.assertEqual(self.model._fields['comment3'].sanitize_attributes, True)
        self.assertEqual(self.model._fields['comment3'].strip_classes, True)

        some_ugly_html = """<p>Oops this should maybe be sanitized
% if object.some_field and not object.oriented:
<table>
    % if object.other_field:
    <tr style="margin: 0px; border: 10px solid black;">
        ${object.mako_thing}
        <td>
    </tr>
    <tr class="custom_class">
        This is some html.
    </tr>
    % endif
    <tr>
%if object.dummy_field:
        <p>Youpie</p>
%endif"""

        record = self.model.create({
            'comment1': some_ugly_html,
            'comment2': some_ugly_html,
            'comment3': some_ugly_html,
            'comment4': some_ugly_html,
        })

        self.assertEqual(record.comment1, some_ugly_html, 'Error in HTML field: content was sanitized but field has sanitize=False')

        self.assertIn('<tr class="', record.comment2)

        # sanitize should have closed tags left open in the original html
        self.assertIn('</table>', record.comment3, 'Error in HTML field: content does not seem to have been sanitized despise sanitize=True')
        self.assertIn('</td>', record.comment3, 'Error in HTML field: content does not seem to have been sanitized despise sanitize=True')
        self.assertIn('<tr style="', record.comment3, 'Style attr should not have been stripped')
        # sanitize does not keep classes if asked to
        self.assertNotIn('<tr class="', record.comment3)

        self.assertNotIn('<tr style="', record.comment4, 'Style attr should have been stripped')


class TestMagicFields(common.TransactionCase):

    def test_write_date(self):
        record = self.env['test_new_api.discussion'].create({'name': 'Booba'})
        self.assertEqual(record.create_uid, self.env.user)
        self.assertEqual(record.write_uid, self.env.user)
