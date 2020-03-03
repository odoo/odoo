#
# test cases for new-style fields
#
from datetime import date, datetime

from odoo.exceptions import AccessError, except_orm
from odoo.tests import common
from odoo.tools import mute_logger, float_repr, pycompat


class TestFields(common.TransactionCase):

    def test_00_basics(self):
        """ test accessing new fields """
        # find a discussion
        discussion = self.env.ref('test_new_api.discussion_0')

        # read field as a record attribute or as a record item
        self.assertIsInstance(discussion.name, pycompat.string_types)
        self.assertIsInstance(discussion['name'], pycompat.string_types)
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

    def test_10_computed_custom(self):
        """ check definition of custom computed fields """
        self.env['ir.model.fields'].create({
            'name': 'x_bool_false_computed',
            'model_id': self.env.ref('test_new_api.model_test_new_api_message').id,
            'field_description': 'A boolean computed to false',
            'compute': "for r in self: r['x_bool_false_computed'] = False",
            'store': False,
            'ttype': 'boolean'
        })
        field = self.env['test_new_api.message']._fields['x_bool_false_computed']
        self.assertFalse(field.depends)

    def test_10_display_name(self):
        """ test definition of automatic field 'display_name' """
        field = type(self.env['test_new_api.discussion']).display_name
        self.assertTrue(field.automatic)
        self.assertTrue(field.compute)
        self.assertEqual(field.depends, ('name',))

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

    def test_11_stored_protected(self):
        """ test protection against recomputation """
        model = self.env['test_new_api.compute.protected']
        field = model._fields['bar']

        record = model.create({'foo': 'unprotected #1'})
        self.assertEqual(record.bar, 'unprotected #1')

        record.write({'foo': 'unprotected #2'})
        self.assertEqual(record.bar, 'unprotected #2')

        # by protecting 'bar', we prevent it from being recomputed
        with self.env.protecting([field], record):
            record.write({'foo': 'protected'})
            self.assertEqual(record.bar, 'unprotected #2')

            # also works when nested
            with self.env.protecting([field], record):
                record.write({'foo': 'protected'})
                self.assertEqual(record.bar, 'unprotected #2')

            record.write({'foo': 'protected'})
            self.assertEqual(record.bar, 'unprotected #2')

        record.write({'foo': 'unprotected #3'})
        self.assertEqual(record.bar, 'unprotected #3')

        # we protect 'bar' on a different record
        with self.env.protecting([field], record):
            record2 = model.create({'foo': 'unprotected'})
            self.assertEqual(record2.bar, 'unprotected')

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

        # rename several records to trigger several recomputations at once
        (d + c + b).write({'name': 'X'})
        self.assertEqual(a.display_name, 'A')
        self.assertEqual(b.display_name, 'X')
        self.assertEqual(c.display_name, 'X / X')
        self.assertEqual(d.display_name, 'X / X / X')

        # delete b; both c and d are deleted in cascade; c should also be marked
        # to recompute, but recomputation should not fail...
        b.unlink()
        self.assertEqual((a + b + c + d).exists(), a)

    def test_12_cascade(self):
        """ test computed field depending on computed field """
        message = self.env.ref('test_new_api.message_0_0')
        message.invalidate_cache()
        double_size = message.double_size
        self.assertEqual(double_size, message.size)

        record = self.env['test_new_api.cascade'].create({'foo': "Hi"})
        self.assertEqual(record.baz, "<[Hi]>")
        record.foo = "Ho"
        self.assertEqual(record.baz, "<[Ho]>")

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

        # write on non-stored inverse field on severals records
        foo1 = Category.create({'name': 'Foo'})
        foo2 = Category.create({'name': 'Foo'})
        (foo1 + foo2).write({'display_name': 'Bar'})
        self.assertEqual(foo1.name, 'Bar')
        self.assertEqual(foo2.name, 'Bar')

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

    def test_13_inverse_access(self):
        """ test access rights on inverse fields """
        foo = self.env['test_new_api.category'].create({'name': 'Foo'})
        user = self.env['res.users'].create({'name': 'Foo', 'login': 'foo'})
        self.assertFalse(user.has_group('base.group_system'))
        # add group on non-stored inverse field
        self.patch(type(foo).display_name, 'groups', 'base.group_system')
        with self.assertRaises(AccessError):
            foo.sudo(user).display_name = 'Forbidden'

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

    def check_monetary(self, record, amount, currency, msg=None):
        # determine the possible roundings of amount
        if currency:
            ramount = currency.round(amount)
            samount = float(float_repr(ramount, currency.decimal_places))
        else:
            ramount = samount = amount

        # check the currency on record
        self.assertEqual(record.currency_id, currency)

        # check the value on the record
        self.assertIn(record.amount, [ramount, samount], msg)

        # check the value in the database
        self.cr.execute('SELECT amount FROM test_new_api_mixed WHERE id=%s', [record.id])
        value = self.cr.fetchone()[0]
        self.assertEqual(value, samount, msg)

    def test_20_monetary(self):
        """ test monetary fields """
        model = self.env['test_new_api.mixed']
        currency = self.env['res.currency'].with_context(active_test=False)
        amount = 14.70126

        for rounding in [0.01, 0.0001, 1.0, 0]:
            # first retrieve a currency corresponding to rounding
            if rounding:
                currency = currency.search([('rounding', '=', rounding)], limit=1)
                self.assertTrue(currency, "No currency found for rounding %s" % rounding)
            else:
                # rounding=0 corresponds to currency=False
                currency = currency.browse()

            # case 1: create with amount and currency
            record = model.create({'amount': amount, 'currency_id': currency.id})
            self.check_monetary(record, amount, currency, 'create(amount, currency)')

            # case 2: assign amount
            record.amount = 0
            record.amount = amount
            self.check_monetary(record, amount, currency, 'assign(amount)')

            # case 3: write with amount and currency
            record.write({'amount': 0, 'currency_id': False})
            record.write({'amount': amount, 'currency_id': currency.id})
            self.check_monetary(record, amount, currency, 'write(amount, currency)')

            # case 4: write with amount only
            record.write({'amount': 0})
            record.write({'amount': amount})
            self.check_monetary(record, amount, currency, 'write(amount)')

            # case 5: write with amount on several records
            records = record + model.create({'currency_id': currency.id})
            records.write({'amount': 0})
            records.write({'amount': amount})
            for record in records:
                self.check_monetary(record, amount, currency, 'multi write(amount)')

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

        # create values for many2one field
        tag0 = self.env['test_new_api.multi.tag'].create({'name': 'Qux'})
        tag1 = self.env['test_new_api.multi.tag'].create({'name': 'Quux'})
        tag2 = self.env['test_new_api.multi.tag'].create({'name': 'Quuz'})

        # create default values for the company-dependent fields
        field_foo = self.env['ir.model.fields']._get('test_new_api.company', 'foo')
        self.env['ir.property'].create({'name': 'foo', 'fields_id': field_foo.id,
                                        'value': 'default', 'type': 'char'})
        field_tag_id = self.env['ir.model.fields']._get('test_new_api.company', 'tag_id')
        self.env['ir.property'].create({'name': 'foo', 'fields_id': field_tag_id.id,
                                        'value': tag0, 'type': 'many2one'})

        # assumption: users don't have access to 'ir.property'
        accesses = self.env['ir.model.access'].search([('model_id.model', '=', 'ir.property')])
        accesses.write(dict.fromkeys(['perm_read', 'perm_write', 'perm_create', 'perm_unlink'], False))

        # create/modify a record, and check the value for each user
        record = self.env['test_new_api.company'].create({
            'foo': 'main',
            'date': '1932-11-09',
            'moment': '1932-11-09 00:00:00',
            'tag_id': tag1.id,
        })
        record.invalidate_cache()
        self.assertEqual(record.sudo(user0).foo, 'main')
        self.assertEqual(record.sudo(user1).foo, 'default')
        self.assertEqual(record.sudo(user2).foo, 'default')
        self.assertEqual(record.sudo(user0).date, '1932-11-09')
        self.assertEqual(record.sudo(user1).date, False)
        self.assertEqual(record.sudo(user2).date, False)
        self.assertEqual(record.sudo(user0).moment, '1932-11-09 00:00:00')
        self.assertEqual(record.sudo(user1).moment, False)
        self.assertEqual(record.sudo(user2).moment, False)
        self.assertEqual(record.sudo(user0).tag_id, tag1)
        self.assertEqual(record.sudo(user1).tag_id, tag0)
        self.assertEqual(record.sudo(user2).tag_id, tag0)

        record.sudo(user1).write({
            'foo': 'alpha',
            'date': '1932-12-10',
            'moment': '1932-12-10 23:59:59',
            'tag_id': tag2.id,
        })
        record.invalidate_cache()
        self.assertEqual(record.sudo(user0).foo, 'main')
        self.assertEqual(record.sudo(user1).foo, 'alpha')
        self.assertEqual(record.sudo(user2).foo, 'default')
        self.assertEqual(record.sudo(user0).date, '1932-11-09')
        self.assertEqual(record.sudo(user1).date, '1932-12-10')
        self.assertEqual(record.sudo(user2).date, False)
        self.assertEqual(record.sudo(user0).moment, '1932-11-09 00:00:00')
        self.assertEqual(record.sudo(user1).moment, '1932-12-10 23:59:59')
        self.assertEqual(record.sudo(user2).moment, False)
        self.assertEqual(record.sudo(user0).tag_id, tag1)
        self.assertEqual(record.sudo(user1).tag_id, tag2)
        self.assertEqual(record.sudo(user2).tag_id, tag0)

        # unlink value of a many2one (tag2), and check again
        tag2.unlink()
        self.assertEqual(record.sudo(user0).tag_id, tag1)
        self.assertEqual(record.sudo(user1).tag_id, tag0.browse())
        self.assertEqual(record.sudo(user2).tag_id, tag0)

        record.sudo(user1).foo = False
        record.invalidate_cache()
        self.assertEqual(record.sudo(user0).foo, 'main')
        self.assertEqual(record.sudo(user1).foo, False)
        self.assertEqual(record.sudo(user2).foo, 'default')

        # set field with 'force_company' in context
        record.sudo(user0).with_context(force_company=company1.id).foo = 'beta'
        record.invalidate_cache()
        self.assertEqual(record.sudo(user0).foo, 'main')
        self.assertEqual(record.sudo(user1).foo, 'beta')
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

        # add group on company-dependent field
        self.assertFalse(user0.has_group('base.group_system'))
        self.patch(type(record).foo, 'groups', 'base.group_system')
        with self.assertRaises(AccessError):
            record.sudo(user0).foo = 'forbidden'

        user0.write({'groups_id': [(4, self.env.ref('base.group_system').id)]})
        record.sudo(user0).foo = 'yes we can'

        # add ir.rule to prevent access on record
        self.assertTrue(user0.has_group('base.group_user'))
        rule = self.env['ir.rule'].create({
            'model_id': self.env['ir.model']._get_id(record._name),
            'groups': [self.env.ref('base.group_user').id],
            'domain_force': str([('id', '!=', record.id)]),
        })
        with self.assertRaises(AccessError):
            record.sudo(user0).foo = 'forbidden'

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

        # take a discussion, use mapped(), and check prefetching
        self.env.clear()
        discussion = self.env.ref('test_new_api.discussion_0')
        discussion.mapped('messages.name')
        # message authors are ready to prefetch
        self.assertTrue(discussion._prefetch.get('res.users'))

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

        with self.env.do_in_onchange():
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

        with self.env.do_in_onchange():
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

    def test_70_x2many_write(self):
        discussion = self.env.ref('test_new_api.discussion_0')
        Message = self.env['test_new_api.message']
        # There must be 3 messages, 0 important
        self.assertEqual(len(discussion.messages), 3)
        self.assertEqual(len(discussion.important_messages), 0)
        self.assertEqual(len(discussion.very_important_messages), 0)
        discussion.important_messages = [(0, 0, {
            'body': 'What is the answer?',
            'important': True,
        })]
        # There must be 4 messages, 1 important
        self.assertEqual(len(discussion.messages), 4)
        self.assertEqual(len(discussion.important_messages), 1)
        self.assertEqual(len(discussion.very_important_messages), 1)
        discussion.very_important_messages |= Message.new({
            'body': '42',
            'important': True,
        })
        # There must be 5 messages, 2 important
        self.assertEqual(len(discussion.messages), 5)
        self.assertEqual(len(discussion.important_messages), 2)
        self.assertEqual(len(discussion.very_important_messages), 2)

    def test_70_x2many_write(self):
        discussion = self.env.ref('test_new_api.discussion_0')
        Message = self.env['test_new_api.message']
        # There must be 3 messages, 0 important
        self.assertEqual(len(discussion.messages), 3)
        self.assertEqual(len(discussion.important_messages), 0)
        self.assertEqual(len(discussion.very_important_messages), 0)
        discussion.important_messages = [(0, 0, {
            'body': 'What is the answer?',
            'important': True,
        })]
        # There must be 4 messages, 1 important
        self.assertEqual(len(discussion.messages), 4)
        self.assertEqual(len(discussion.important_messages), 1)
        self.assertEqual(len(discussion.very_important_messages), 1)
        discussion.very_important_messages |= Message.new({
            'body': '42',
            'important': True,
        })
        # There must be 5 messages, 2 important
        self.assertEqual(len(discussion.messages), 5)
        self.assertEqual(len(discussion.important_messages), 2)
        self.assertEqual(len(discussion.very_important_messages), 2)


class TestX2many(common.TransactionCase):
    def test_search_many2many(self):
        """ Tests search on many2many fields. """
        tags = self.env['test_new_api.multi.tag']
        tagA = tags.create({})
        tagB = tags.create({})
        tagC = tags.create({})
        recs = self.env['test_new_api.multi.line']
        recW = recs.create({})
        recX = recs.create({'tags': [(4, tagA.id)]})
        recY = recs.create({'tags': [(4, tagB.id)]})
        recZ = recs.create({'tags': [(4, tagA.id), (4, tagB.id)]})
        recs = recW + recX + recY + recZ

        # test 'in'
        result = recs.search([('tags', 'in', (tagA + tagB).ids)])
        self.assertEqual(result, recX + recY + recZ)

        result = recs.search([('tags', 'in', tagA.ids)])
        self.assertEqual(result, recX + recZ)

        result = recs.search([('tags', 'in', tagB.ids)])
        self.assertEqual(result, recY + recZ)

        result = recs.search([('tags', 'in', tagC.ids)])
        self.assertEqual(result, recs.browse())

        result = recs.search([('tags', 'in', [])])
        self.assertEqual(result, recs.browse())

        # test 'not in'
        result = recs.search([('id', 'in', recs.ids), ('tags', 'not in', (tagA + tagB).ids)])
        self.assertEqual(result, recs - recX - recY - recZ)

        result = recs.search([('id', 'in', recs.ids), ('tags', 'not in', tagA.ids)])
        self.assertEqual(result, recs - recX - recZ)

        result = recs.search([('id', 'in', recs.ids), ('tags', 'not in', tagB.ids)])
        self.assertEqual(result, recs - recY - recZ)

        result = recs.search([('id', 'in', recs.ids), ('tags', 'not in', tagC.ids)])
        self.assertEqual(result, recs)

        result = recs.search([('id', 'in', recs.ids), ('tags', 'not in', [])])
        self.assertEqual(result, recs)

        # special case: compare with False
        result = recs.search([('id', 'in', recs.ids), ('tags', '=', False)])
        self.assertEqual(result, recW)

        result = recs.search([('id', 'in', recs.ids), ('tags', '!=', False)])
        self.assertEqual(result, recs - recW)

    def test_search_one2many(self):
        """ Tests search on one2many fields. """
        recs = self.env['test_new_api.multi']
        recX = recs.create({'lines': [(0, 0, {}), (0, 0, {})]})
        recY = recs.create({'lines': [(0, 0, {})]})
        recZ = recs.create({})
        recs = recX + recY + recZ
        line1, line2, line3 = recs.mapped('lines')
        line4 = recs.create({'lines': [(0, 0, {})]}).lines
        line0 = line4.create({})

        # test 'in'
        result = recs.search([('id', 'in', recs.ids), ('lines', 'in', (line1 + line2 + line3 + line4).ids)])
        self.assertEqual(result, recX + recY)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'in', (line1 + line3 + line4).ids)])
        self.assertEqual(result, recX + recY)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'in', (line1 + line4).ids)])
        self.assertEqual(result, recX)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'in', line4.ids)])
        self.assertEqual(result, recs.browse())

        result = recs.search([('id', 'in', recs.ids), ('lines', 'in', [])])
        self.assertEqual(result, recs.browse())

        # test 'not in'
        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', (line1 + line2 + line3).ids)])
        self.assertEqual(result, recs - recX - recY)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', (line1 + line3).ids)])
        self.assertEqual(result, recs - recX - recY)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', line1.ids)])
        self.assertEqual(result, recs - recX)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', (line1 + line4).ids)])
        self.assertEqual(result, recs - recX)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', line4.ids)])
        self.assertEqual(result, recs)

        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', [])])
        self.assertEqual(result, recs)

        # these cases are weird
        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', (line1 + line0).ids)])
        self.assertEqual(result, recs.browse())

        result = recs.search([('id', 'in', recs.ids), ('lines', 'not in', line0.ids)])
        self.assertEqual(result, recs.browse())

        # special case: compare with False
        result = recs.search([('id', 'in', recs.ids), ('lines', '=', False)])
        self.assertEqual(result, recZ)

        result = recs.search([('id', 'in', recs.ids), ('lines', '!=', False)])
        self.assertEqual(result, recs - recZ)

    def test_custom_m2m(self):
        model_id = self.env['ir.model']._get_id('res.partner')
        field = self.env['ir.model.fields'].create({
            'name': 'x_foo',
            'field_description': 'Foo',
            'model_id': model_id,
            'ttype': 'many2many',
            'relation': 'res.country',
            'store': False,
        })
        self.assertTrue(field.unlink())


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
