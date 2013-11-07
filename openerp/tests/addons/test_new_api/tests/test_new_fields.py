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
        self.Partner = self.registry('res.partner')
        self.User = self.registry('res.users')

    def test_00_basics(self):
        """ test accessing new fields """
        # find a partner
        partner = self.Partner.search([('name', 'ilike', 'j')])[0]

        # read field as a record attribute
        self.assertIsInstance(partner.children_count, (int, long))

        # read field as a record item
        self.assertIsInstance(partner['children_count'], (int, long))
        self.assertEqual(partner['children_count'], partner.children_count)

        # read field as a record item
        values = partner.read(['children_count'])[0]
        self.assertIsInstance(values, dict)
        self.assertIsInstance(values['children_count'], (int, long))
        self.assertEqual(values['children_count'], partner.children_count)

    def test_10_non_stored(self):
        """ test non-stored fields """
        # find partners
        alpha, beta, gamma = self.Partner.search([], limit=3)

        # check definition of the field
        self.assertEqual(alpha.name_size, len(alpha.name))
        self.assertEqual(beta.name_size, len(beta.name))
        self.assertEqual(gamma.name_size, len(gamma.name))

        # check recomputation after record is modified
        alpha_name = alpha.name
        alpha_size = len(alpha_name)
        for n in xrange(10):
            alpha.write({'name': alpha_name + ("!" * n)})
            self.assertEqual(alpha.name_size, alpha_size + n)

    def test_11_stored(self):
        """ test stored fields """
        # find partners with children
        alpha, beta, gamma = self.Partner.search([('child_ids.name', '!=', False)], limit=3)

        # check regular field
        alpha.write({'number_of_employees': 10})
        self.assertEqual(alpha.number_of_employees, 10)

        alpha.number_of_employees = 20
        self.assertEqual(alpha.number_of_employees, 20)
        alpha.invalidate_cache(['number_of_employees'])
        self.assertEqual(alpha.number_of_employees, 20)

        # check definition of the field
        self.assertEqual(alpha.children_count, len(alpha.child_ids))
        self.assertEqual(beta.children_count, len(beta.child_ids))
        self.assertEqual(gamma.children_count, len(gamma.child_ids))

        # check recomputation after children are deleted
        alpha_count = alpha.children_count
        for n, child in enumerate(alpha.child_ids, start=1):
            child.unlink()
            self.assertEqual(alpha.children_count, alpha_count - n)

        # check recomputation after children are created
        self.assertEqual(alpha.children_count, 0)
        foo = self.Partner.create({'name': 'Foo', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 1)
        self.assertFalse(foo.has_sibling)
        self.Partner.create({'name': 'Bar', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 2)
        self.assertTrue(foo.has_sibling)
        self.Partner.create({'name': 'Baz', 'parent_id': alpha.id})
        self.assertEqual(alpha.children_count, 3)
        self.assertTrue(foo.has_sibling)

        # check recomputation after children are transfered to another partner
        children = beta.child_ids + gamma.child_ids
        beta_count = beta.children_count
        gamma_count = gamma.children_count
        for n, child in enumerate(beta.child_ids, start=1):
            child.write({'parent_id': gamma.id})
            self.assertEqual(beta.children_count, beta_count - n)
            self.assertEqual(gamma.children_count, gamma_count + n)
            for c in children:
                self.assertEqual(c.has_sibling, c.parent_id.children_count >= 2)

    def test_12_recursive(self):
        """ test recursively dependent fields """
        raise NotImplementedError()
        abel = self.Partner.create({'name': 'Abel'})
        beth = self.Partner.create({'name': 'Bethany'})
        cath = self.Partner.create({'name': 'Catherine'})
        dean = self.Partner.create({'name': 'Dean'})
        ethan = self.Partner.create({'name': 'Ethan'})
        fanny = self.Partner.create({'name': 'Fanny'})
        gabriel = self.Partner.create({'name': 'Gabriel'})

        beth.parent_id = abel
        cath.parent_id = abel
        dean.parent_id = beth
        ethan.parent_id = beth
        fanny.parent_id = beth
        gabriel.parent_id = cath

        self.assertEqual(abel.child_ids, beth | cath)
        self.assertEqual(beth.child_ids, dean | ethan | fanny)
        self.assertEqual(cath.child_ids, gabriel)

        self.assertEqual(abel.family_size, 7)
        self.assertEqual(beth.family_size, 4)
        self.assertEqual(cath.family_size, 2)
        self.assertEqual(dean.family_size, 1)
        self.assertEqual(ethan.family_size, 1)
        self.assertEqual(fanny.family_size, 1)
        self.assertEqual(gabriel.family_size, 1)

    def test_13_inverse(self):
        """ test inverse computation of fields """
        model = self.registry('test_new_api.inverse')

        joe = model.create({'name': 'Joe the plumber', 'email': 'joe@example.com'})
        self.assertEqual(joe.name, 'Joe the plumber')
        self.assertEqual(joe.email, 'joe@example.com')
        self.assertEqual(joe.full_name, 'Joe the plumber <joe@example.com>')

        joe.name = 'Joseph Singer'
        self.assertEqual(joe.full_name, 'Joseph Singer <joe@example.com>')

        joe.email = 'joe@openerp.com'
        self.assertEqual(joe.full_name, 'Joseph Singer <joe@openerp.com>')

        joe.full_name = 'Joe Bailey <joe.bailey@whisky.com>'
        self.assertEqual(joe.name, 'Joe Bailey')
        self.assertEqual(joe.email, 'joe.bailey@whisky.com')

    def test_14_search(self):
        """ test search on computed fields """
        all_ps = self.Partner.search([])

        # partition all partners based on their name size
        partners_by_size = defaultdict(self.Partner.browse)
        for p in all_ps:
            partners_by_size[p.name_size] += p

        max_size = max(partners_by_size)
        for size in xrange(max_size + 1):
            ps = self.Partner.search([('name_size', '=', size)])
            self.assertEqual(ps, partners_by_size[size])

        # check other comparisons
        ps = self.Partner.search([('name_size', '>=', 6), ('name_size', '<', 12)])
        qs = sum((p for p in all_ps if p.name_size >= 6 and p.name_size < 12),
                 self.Partner.browse())
        self.assertEqual(ps, qs)

    def test_15_constraint(self):
        """ test new-style Python constraints """
        model = self.registry('test_new_api.inverse')
        record = model.create({'name': 'Joe the plumber', 'email': 'joe@example.com'})

        with self.assertRaises(Exception):
            record.name = "Joe @ home"

        with self.assertRaises(Exception):
            record.email = "joe.the.plumber"

    def test_20_float(self):
        """ test float fields """
        # find a partner
        alpha = self.Partner.search([], limit=1)[0]

        # assign value, and expect rounding
        alpha.write({'some_float_field': 2.4999999999999996})
        self.assertEqual(alpha.some_float_field, 2.50)

        # same with field setter
        alpha.some_float_field = 2.4999999999999996
        self.assertEqual(alpha.some_float_field, 2.50)

    def test_21_date(self):
        """ test date fields """
        # find a partner
        alpha = self.Partner.search([], limit=1)[0]

        # one may assign False or None
        alpha.date = None
        self.assertIs(alpha.date, False)

        # one may assign date and datetime objects
        alpha.date = date(2012, 05, 01)
        self.assertEqual(alpha.date, '2012-05-01')

        alpha.date = datetime(2012, 05, 01, 10, 45, 00)
        self.assertEqual(alpha.date, '2012-05-01')

        # one may assign dates in the default format, and it must be checked
        alpha.date = '2012-05-01'
        self.assertEqual(alpha.date, '2012-05-01')

        with self.assertRaises(ValueError):
            alpha.date = '12-5-1'

    def test_22_selection(self):
        """ test selection fields """
        # find a partner
        alpha = self.Partner.search([], limit=1)[0]

        # one may assign False or None
        alpha.type = None
        self.assertIs(alpha.type, False)

        # one may assign a value, and it must be checked
        alpha.type = 'delivery'
        with self.assertRaises(ValueError):
            alpha.type = 'notacorrectvalue'

        # same with dynamic selections
        for language in self.registry('res.lang').search([]):
            alpha.lang = language.code
        with self.assertRaises(ValueError):
            alpha.lang = 'zz_ZZ'

    def test_23_relation(self):
        """ test relation fields """
        outer_scope = scope.current
        demo = self.User.search([('login', '=', 'demo')]).one()

        # retrieve two partners with children
        alpha, beta = self.Partner.search([('child_ids', '!=', False)], limit=2)
        alpha1 = alpha.child_ids[0]

        # check scope of records
        self.assertEqual(alpha1._scope, outer_scope)
        self.assertEqual(beta._scope, outer_scope)

        with scope(user=demo) as inner_scope:
            self.assertNotEqual(inner_scope, outer_scope)

            # assign alpha1's parent to a record in inner scope
            inner_beta = beta.scoped()
            alpha1.parent_id = inner_beta

            # both alpha1 and its parent field must be in outer scope
            self.assertEqual(alpha1._scope, outer_scope)
            self.assertEqual(alpha1.parent_id._scope, outer_scope)

            # migrate alpha1 into the current scope, and check again
            inner_alpha1 = alpha1.scoped()
            self.assertEqual(inner_alpha1._scope, inner_scope)
            self.assertEqual(inner_alpha1.parent_id._scope, inner_scope)

    def test_24_reference(self):
        """ test reference fields. """
        alpha, beta = self.Partner.search([], limit=2)

        # one may assign False or None
        alpha.some_reference_field = None
        self.assertIs(alpha.some_reference_field, False)

        # one may assign a partner or a user
        alpha.some_reference_field = beta
        self.assertEqual(alpha.some_reference_field, beta)
        alpha.some_reference_field = self.scope.user
        self.assertEqual(alpha.some_reference_field, self.scope.user)
        with self.assertRaises(ValueError):
            alpha.some_reference_field = self.scope.user.company_id

    def test_25_related(self):
        """ test related fields. """
        partner = self.Partner.search([('company_id', '!=', False)], limit=1)[0]
        company = partner.company_id

        # check value of related field
        self.assertEqual(partner.company_name, company.name)
        self.assertEqual(partner['company_name'], company.name)

        # change company name, and check result
        company.name = 'Foo'
        self.assertEqual(partner.company_name, 'Foo')
        self.assertEqual(partner['company_name'], 'Foo')

        # change company name via related field, and check result
        partner.company_name = 'Bar'
        self.assertEqual(company.name, 'Bar')
        self.assertEqual(partner.company_name, 'Bar')
        self.assertEqual(partner['company_name'], 'Bar')

        # search on related field, and check result
        search_on_related = self.Partner.search([('company_name', '=', 'Bar')])
        search_on_regular = self.Partner.search([('company_id.name', '=', 'Bar')])
        self.assertEqual(search_on_related, search_on_regular)

        # check that field attributes are copied
        partner_field = partner.fields_get(['company_name'])['company_name']
        company_field = company.fields_get(['name'])['name']
        self.assertEqual(partner_field['required'], company_field['required'])

    def test_26_inherited(self):
        """ test inherited fields. """
        # a bunch of fields are inherited from res_partner
        for user in self.User.search([]):
            partner = user.partner_id
            for field in ('is_company', 'name', 'email', 'country_id'):
                self.assertEqual(getattr(user, field), getattr(partner, field))
                self.assertEqual(user[field], partner[field])

    def test_30_read(self):
        """ test computed fields as returned by read(). """
        alpha = self.Partner.search([], limit=1).one()

        name_size = alpha.name_size
        company = alpha.computed_company
        companies = alpha.computed_companies

        data = alpha.read(['name_size', 'computed_company', 'computed_companies'])[0]
        self.assertEqual(data['name_size'], name_size)
        self.assertEqual(data['computed_company'], company.name_get()[0])
        self.assertEqual(data['computed_companies'], companies.unbrowse())

    def test_40_new(self):
        """ test new records. """
        # create a new partner
        partner = self.Partner.new()
        self.assertFalse(partner.id)

        # assign some fields; should have no side effect
        partner.name = "Foo"
        self.assertEqual(partner.name, "Foo")

        children = self.Partner.search([('parent_id', '=', False)], limit=2)
        partner.child_ids = children
        self.assertEqual(partner.child_ids, children)

        # check computed values of fields
        self.assertEqual(partner.active, True)
        self.assertEqual(partner.number_of_employees, 1)
        self.assertEqual(partner.name_size, 3)
        self.assertEqual(partner.children_count, 2)

    def test_41_defaults(self):
        """ test default values. """
        fields = ['name', 'active', 'number_of_employees', 'name_size']
        defaults = self.Partner.default_get(fields)

        self.assertFalse(defaults.get('name'))
        self.assertFalse(defaults.get('name_size'))
        self.assertEqual(defaults['active'], True)
        self.assertEqual(defaults['number_of_employees'], 1)

        fields = ['name', 'description']
        defaults = self.registry('test_new_api.defaults').default_get(fields)
        self.assertEqual(defaults.get('name'), u"Bob the Builder")

class TestMagicalFields(common.TransactionCase):

    def setUp(self):
        super(TestMagicalFields, self).setUp()
        self.Model = self.registry('test_new_api.on_change')

    def test_write_date(self):
        record = self.Model.create({'name': 'Booba'})

        self.assertEqual(
            record.write_uid,
            self.registry('res.users').browse(self.uid))

class TestInherits(common.TransactionCase):
    def setUp(self):
        super(TestInherits, self).setUp()
        self.Parent = self.registry('test_new_api.inherits_parent')
        self.Child = self.registry('test_new_api.inherits_child')

    def test_inherits(self):
        """ Check that a many2one field with delegate=True adds an entry in _inherits """
        self.assertEqual(self.Child._inherits, {'test_new_api.inherits_parent': 'parent'})
        self.assertIn('name', self.Child._fields)
        self.assertEqual(self.Child._fields['name'].related, ('parent', 'name'))

        child = self.Child.create({'name': 'Foo'})
        parent = child.parent
        self.assertTrue(parent)
        self.assertEqual(child._name, 'test_new_api.inherits_child')
        self.assertEqual(parent._name, 'test_new_api.inherits_parent')
        self.assertEqual(child.name, parent.name)
