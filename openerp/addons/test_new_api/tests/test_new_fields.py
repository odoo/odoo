#
# test cases for new-style fields
#
from datetime import date, datetime
from collections import defaultdict

from openerp import scope
from openerp.tests import common


class TestNewFields(common.TransactionCase):

    def setUp(self):
        super(TestNewFields, self).setUp()
        self.Category = scope['test_new_api.category']
        self.Discussion = scope['test_new_api.discussion']
        self.Message = scope['test_new_api.message']
        self.Mixed = scope['test_new_api.mixed']

    def test_00_basics(self):
        """ test accessing new fields """
        # find a discussion
        discussion = scope.ref('test_new_api.discussion_0')

        # read field as a record attribute or as a record item
        self.assertIsInstance(discussion.name, basestring)
        self.assertIsInstance(discussion['name'], basestring)
        self.assertEqual(discussion['name'], discussion.name)

        # read it with method read()
        values = discussion.read(['name'])[0]
        self.assertEqual(values['name'], discussion.name)

    def test_10_non_stored(self):
        """ test non-stored fields """
        # find messages
        for message in self.Message.search([]):
            # check definition of field
            self.assertEqual(message.size, len(message.body or ''))

            # check recomputation after record is modified
            size = message.size
            message.write({'body': (message.body or '') + "!!!"})
            self.assertEqual(message.size, size + 3)

    def test_11_stored(self):
        """ test stored fields """
        # find the demo discussion
        discussion = scope.ref('test_new_api.discussion_0')
        self.assertTrue(len(discussion.messages) > 0)

        # check messages
        name0 = discussion.name or ""
        for message in discussion.messages:
            self.assertEqual(message.name, "[%s] %s" % (name0, message.author.name))

        # modify discussion name, and check again messages
        discussion.name = name1 = 'Talking about stuff...'
        for message in discussion.messages:
            self.assertEqual(message.name, "[%s] %s" % (name1, message.author.name))

        # switch message from discussion, and check again
        name2 = 'Another discussion'
        discussion2 = discussion.copy({'name': name2})
        message2 = discussion.messages[0]
        message2.discussion = discussion2
        for message in discussion2.messages:
            self.assertEqual(message.name, "[%s] %s" % (name2, message.author.name))

    def test_12_recursive(self):
        """ test recursively dependent fields """
        abel = self.Category.create({'name': 'Abel'})
        beth = self.Category.create({'name': 'Bethany'})
        cath = self.Category.create({'name': 'Catherine'})
        dean = self.Category.create({'name': 'Dean'})
        ewan = self.Category.create({'name': 'Ewan'})
        finn = self.Category.create({'name': 'Finnley'})
        gabe = self.Category.create({'name': 'Gabriel'})

        beth.parent = cath.parent = abel
        ewan.parent = finn.parent = beth
        gabe.parent = cath

        self.assertEqual(ewan.display_name, "Abel / Bethany / Ewan")
        self.assertEqual(finn.display_name, "Abel / Bethany / Finnley")
        self.assertEqual(beth.display_name, "Abel / Bethany")
        self.assertEqual(gabe.display_name, "Abel / Catherine / Gabriel")

        ewan.parent = cath
        self.assertEqual(ewan.display_name, "Abel / Catherine / Ewan")

        cath.parent = beth
        self.assertEqual(ewan.display_name, "Abel / Bethany / Catherine / Ewan")

    def test_13_inverse(self):
        """ test inverse computation of fields """
        abel = self.Category.create({'name': 'Abel'})
        beth = self.Category.create({'name': 'Bethany'})
        cath = self.Category.create({'name': 'Catherine'})
        dean = self.Category.create({'name': 'Dean'})
        ewan = self.Category.create({'name': 'Ewan'})
        finn = self.Category.create({'name': 'Finnley'})
        gabe = self.Category.create({'name': 'Gabriel'})
        self.assertEqual(ewan.display_name, "Ewan")

        ewan.display_name = "Abel / Bethany / Catherine / Erwan"

        self.assertEqual(beth.parent, abel)
        self.assertEqual(cath.parent, beth)
        self.assertEqual(ewan.parent, cath)
        self.assertEqual(ewan.name, "Erwan")

    def test_14_search(self):
        """ test search on computed fields """
        discussion = scope.ref('test_new_api.discussion_0')

        # determine message sizes
        sizes = set(message.size for message in discussion.messages)

        # search for messages based on their size
        for size in sizes:
            messages0 = self.Message.search(
                [('discussion', '=', discussion.id), ('size', '<=', size)])

            messages1 = self.Message.browse()
            for message in discussion.messages:
                if message.size <= size:
                    messages1 += message

            self.assertEqual(messages0, messages1)

    def test_15_constraint(self):
        """ test new-style Python constraints """
        discussion = scope.ref('test_new_api.discussion_0')

        # remove oneself from discussion participants: we can no longer create
        # messages in discussion
        discussion.participants -= scope.user
        with self.assertRaises(Exception):
            self.Message.create({'discussion': discussion.id, 'body': 'Whatever'})

        # put back oneself into discussion participants: now we can create
        # messages in discussion
        discussion.participants += scope.user
        self.Message.create({'discussion': discussion.id, 'body': 'Whatever'})

    def test_20_float(self):
        """ test float fields """
        record = self.Mixed.create({})

        # assign value, and expect rounding
        record.write({'number': 2.4999999999999996})
        self.assertEqual(record.number, 2.50)

        # same with field setter
        record.number = 2.4999999999999996
        self.assertEqual(record.number, 2.50)

    def test_21_date(self):
        """ test date fields """
        record = self.Mixed.create({})

        # one may assign False or None
        record.date = None
        self.assertFalse(record.date)

        # one may assign date and datetime objects
        record.date = date(2012, 05, 01)
        self.assertEqual(record.date, '2012-05-01')

        record.date = datetime(2012, 05, 01, 10, 45, 00)
        self.assertEqual(record.date, '2012-05-01')

        # one may assign dates in the default format, and it must be checked
        record.date = '2012-05-01'
        self.assertEqual(record.date, '2012-05-01')

        with self.assertRaises(ValueError):
            record.date = '12-5-1'

    def test_22_selection(self):
        """ test selection fields """
        record = self.Mixed.create({})

        # one may assign False or None
        record.lang = None
        self.assertFalse(record.lang)

        # one may assign a value, and it must be checked
        for language in scope['res.lang'].search([]):
            record.lang = language.code
        with self.assertRaises(ValueError):
            record.lang = 'zz_ZZ'

    def test_23_relation(self):
        """ test relation fields """
        outer_scope = scope.current

        demo = scope.ref('base.user_demo')
        message = scope.ref('test_new_api.message_0_0')

        # check scope of record and related records
        self.assertEqual(message._scope, outer_scope)
        self.assertEqual(message.discussion._scope, outer_scope)

        with scope(user=demo) as inner_scope:
            self.assertNotEqual(inner_scope, outer_scope)

            # check scope of record and related records
            self.assertEqual(message._scope, outer_scope)
            self.assertEqual(message.discussion._scope, outer_scope)

            # migrate message into the current scope, and check again
            inner_message = message.attach_scope(scope.current)
            self.assertEqual(inner_message._scope, inner_scope)
            self.assertEqual(inner_message.discussion._scope, inner_scope)

            # assign record's parent to a record in inner scope
            message.discussion = message.discussion.copy({'name': 'Copy'})

            # both message and its parent field must be in outer scope
            self.assertEqual(message._scope, outer_scope)
            self.assertEqual(message.discussion._scope, outer_scope)

            # migrate message into the current scope, and check again
            self.assertEqual(inner_message._scope, inner_scope)
            self.assertEqual(inner_message.discussion._scope, inner_scope)

    def test_24_reference(self):
        """ test reference fields. """
        record = self.Mixed.create({})

        # one may assign False or None
        record.reference = None
        self.assertFalse(record.reference)

        # one may assign a user or a partner...
        record.reference = self.scope.user
        self.assertEqual(record.reference, self.scope.user)
        record.reference = self.scope.user.partner_id
        self.assertEqual(record.reference, self.scope.user.partner_id)
        # ... but no record from a model that starts with 'ir.'
        with self.assertRaises(ValueError):
            record.reference = scope['ir.model'].search([], limit=1)

    def test_25_related(self):
        """ test related fields. """
        message = scope.ref('test_new_api.message_0_0')
        discussion = message.discussion

        # check value of related field
        self.assertEqual(message.discussion_name, discussion.name)

        # change discussion name, and check result
        discussion.name = 'Foo'
        self.assertEqual(message.discussion_name, 'Foo')

        # change discussion name via related field, and check result
        message.discussion_name = 'Bar'
        self.assertEqual(discussion.name, 'Bar')
        self.assertEqual(message.discussion_name, 'Bar')

        # search on related field, and check result
        search_on_related = self.Message.search([('discussion_name', '=', 'Bar')])
        search_on_regular = self.Message.search([('discussion.name', '=', 'Bar')])
        self.assertEqual(search_on_related, search_on_regular)

        # check that field attributes are copied
        message_field = message.fields_get(['discussion_name'])['discussion_name']
        discussion_field = discussion.fields_get(['name'])['name']
        self.assertEqual(message_field['required'], discussion_field['required'])

    def test_26_inherited(self):
        """ test inherited fields. """
        # a bunch of fields are inherited from res_partner
        for user in scope['res.users'].search([]):
            partner = user.partner_id
            for field in ('is_company', 'name', 'email', 'country_id'):
                self.assertEqual(getattr(user, field), getattr(partner, field))
                self.assertEqual(user[field], partner[field])

    def test_30_read(self):
        """ test computed fields as returned by read(). """
        discussion = scope.ref('test_new_api.discussion_0')

        for message in discussion.messages:
            display_name = message.display_name
            size = message.size

            data = message.read(['display_name', 'size'])[0]
            self.assertEqual(data['display_name'], display_name)
            self.assertEqual(data['size'], size)

    def test_40_new(self):
        """ test new records. """
        discussion = scope.ref('test_new_api.discussion_0')

        # create a new message
        message = self.Message.new()
        self.assertFalse(message.id)

        # assign some fields; should have no side effect
        message.discussion = discussion
        message.body = BODY = "May the Force be with you."
        self.assertEqual(message.discussion, discussion)
        self.assertEqual(message.body, BODY)

        self.assertNotIn(message, discussion.messages)

        # check computed values of fields
        self.assertEqual(message.author, scope.user)
        self.assertEqual(message.name, "[%s] %s" % (discussion.name, scope.user.name))
        self.assertEqual(message.size, len(BODY))

    def test_41_defaults(self):
        """ test default values. """
        fields = ['discussion', 'body', 'author', 'size']
        defaults = self.Message.default_get(fields)

        self.assertFalse(defaults.get('discussion'))
        self.assertFalse(defaults.get('body'))
        self.assertEqual(defaults['author'], scope.user.id)
        self.assertEqual(defaults['size'], 0)


class TestMagicFields(common.TransactionCase):

    def setUp(self):
        super(TestMagicFields, self).setUp()
        self.Discussion = scope['test_new_api.discussion']

    def test_write_date(self):
        record = self.Discussion.create({'name': 'Booba'})
        self.assertEqual(record.create_uid, scope.user)
        self.assertEqual(record.write_uid, scope.user)


class TestInherits(common.TransactionCase):

    def setUp(self):
        super(TestInherits, self).setUp()
        self.Talk = scope['test_new_api.talk']

    def test_inherits(self):
        """ Check that a many2one field with delegate=True adds an entry in _inherits """
        self.assertEqual(self.Talk._inherits, {'test_new_api.discussion': 'parent'})
        self.assertIn('name', self.Talk._fields)
        self.assertEqual(self.Talk._fields['name'].related, ('parent', 'name'))

        talk = self.Talk.create({'name': 'Foo'})
        discussion = talk.parent
        self.assertTrue(discussion)
        self.assertEqual(talk._name, 'test_new_api.talk')
        self.assertEqual(discussion._name, 'test_new_api.discussion')
        self.assertEqual(talk.name, discussion.name)
