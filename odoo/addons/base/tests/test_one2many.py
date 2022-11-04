# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import combinations
from odoo.osv.expression import invert_domain
from odoo.tests.common import TransactionCase


###############################################################################
# Common base class implementing search and filtered_domain checks            #
###############################################################################


class SearchCase(TransactionCase):
    def check_consistency(self, expected, searched, filtered, domain):
        tests = {
            'expected': True,
            'searched': expected == searched,
            'filtered': expected == filtered,
        }

        right = ' and '.join([key for key, value in tests.items() if value])
        wrong = ' and '.join([key for key, value in tests.items() if not value])
        message = f'The {wrong} results are inconsistent with the {right} results for domain {domain}'
        self.assertTrue(all(test for test in tests.values()), message)

    def execute_test(self, domain, expected):
        base_domain = [('id', 'in', self.parents.ids)]
        inverted_domain = invert_domain(domain)

        searched = self.parent_model.search(base_domain + domain)
        filtered = self.parents.filtered_domain(domain)
        self.check_consistency(expected, searched, filtered, domain)

        expected = self.parents - expected
        searched = self.parent_model.search(base_domain + inverted_domain)
        filtered = self.parents.filtered_domain(inverted_domain)
        self.check_consistency(expected, searched, filtered, inverted_domain)


###############################################################################
# Abstract bases with test definitions                                        #
###############################################################################


class TestOne2ManyBase:
    '''
    This class defines a set of tests where parent records are searched on a
    condition in function of their related records. Between these parent and
    related records a one2many relationship exists (de facto, as such the
    multiplicity of the underlying field can also be many2many).

    A set of n parent records are created as part of the class setup, where the
    parent at index i has exactly i related records.
    '''
    @classmethod
    def prepare_data(cls, n=2):
        cls.path = f'{cls.parent_field}'
        cls.parents = cls.parent_model.create([
            cls.get_parent_values({cls.parent_field: [
                (0, 0, cls.get_child_values(count, index))
                for index in range(count)
            ]}, count) for count in range(n + 1)
        ])

    @classmethod
    def get_child_values(cls, count, index):
        child_name = cls.parent_model[cls.parent_field]._name.split('.')[-1]
        return {'name': f'parent-{count}-{child_name}-{index}'}

    @classmethod
    def get_parent_values(cls, values, count):
        parent_name = cls.parent_model._name.split('.')[-1]
        return {'name': f'{parent_name}-{count}', **values}

    def test_00_equals(self):
        subdomain = [('id', '=', self.parents[1].mapped(self.path)[0].id)]
        domain = [(self.path, 'any', subdomain)]
        self.execute_test(domain, self.parents[1])

    def test_01_not_equals(self):
        subdomain = [('id', '!=', self.parents[1].mapped(self.path)[0].id)]
        domain = [(self.path, 'any', subdomain)]
        self.execute_test(domain, self.parents[2])

        subdomain = [('id', '!=', self.parents[2].mapped(self.path)[0].id)]
        domain = [(self.path, 'any', subdomain)]
        self.execute_test(domain, self.parents[1:3])

    def test_02_equals_false(self):
        domain = [(self.path, 'any', [('id', '=', False)])]
        self.execute_test(domain, self.parent_model)

    def test_03_not_equals_false(self):
        domain = [(self.path, 'any', [('id', '!=', False)])]
        self.execute_test(domain, self.parents[1:3])

        domain = [(self.path, '!=', False)]
        self.execute_test(domain, self.parents[1:3])

    def test_04_all_equals_false(self):
        domain = [(self.path, 'all', [('id', '=', False)])]
        self.execute_test(domain, self.parents[0])

        domain = [(self.path, '=', False)]
        self.execute_test(domain, self.parents[0])

    def test_05_all_not_equals_false(self):
        domain = [(self.path, 'all', [('id', '!=', False)])]
        self.execute_test(domain, self.parents)


class TestMany2ManyBase:
    '''
    This class defines a set of tests where parent records are searched on a
    condition in function of their related records. Between these parent and
    related records a many2many relationship exists.

    Parent records are created, as part of the class setup, related to each
    possible subset of n related records.
    '''
    @classmethod
    def prepare_data(cls, n):
        cls.path = f'{cls.parent_field}'
        cls.children = cls.parent_model[cls.parent_field].create([{
            **cls.get_child_values(i),
        } for i in range(0, n)])
        cls.parents = cls.parent_model.create([
            cls.get_parent_values({cls.parent_field: [(6, 0, [
                cls.children[j].id
                for j in range(0, n) if (1 << j) & i
            ])]}, i) for i in range(0, 2**n)
        ])

    @classmethod
    def get_child_values(cls, index):
        child_name = cls.parent_model[cls.parent_field]._name.split('.')[-1]
        return {'name': f'{child_name}-child-{index}'}

    @classmethod
    def get_parent_values(cls, values, index):
        parent_name = cls.parent_model._name.split('.')[-1]
        return {'name': f'{parent_name}-parent-{index}', **values}

    @classmethod
    def get_parents(cls, children=None):
        def test_parent(parent):
            return all(c.id in parent[cls.parent_field].ids for c in children)
        children = children or cls.parent_model[cls.parent_field]
        return cls.parents.filtered(test_parent)

    def test_00_any_id_equals(self):
        domain = [(self.path, 'any', [('id', '=', self.children[0].id)])]
        self.execute_test(domain, self.get_parents(self.children[0]))

    def test_01_any_id_not_equals(self):
        domain = [(self.path, 'any', [('id', '!=', self.children[0].id)])]
        result = self.get_parents(self.children[1]) | self.get_parents(self.children[2])
        self.execute_test(domain, result)

    def test_02_any_id_equals_false(self):
        domain = [(self.path, 'any', [('id', '=', False)])]
        self.execute_test(domain, self.parent_model)

    def test_03_any_id_not_equals_false(self):
        domain = [(self.path, 'any', [('id', '!=', False)])]
        self.execute_test(domain, self.parents[1:8])

        domain = [(self.path, '!=', False)]
        self.execute_test(domain, self.parents[1:8])

    def test_04_all_id_equals_false(self):
        domain = [(self.path, 'all', [('id', '=', False)])]
        self.execute_test(domain, self.parents[0])

        domain = [(self.path, '=', False)]
        self.execute_test(domain, self.parents[0])

    def test_05_all_id_not_equals_false(self):
        domain = [(self.path, 'all', [('id', '!=', False)])]
        self.execute_test(domain, self.parents)

    def test_06_in(self):
        subdomain = [('id', 'in', self.children[1:3].ids)]
        domain = [(self.path, 'any', subdomain)]
        result = self.get_parents(self.children[1]) | self.get_parents(self.children[2])
        self.execute_test(domain, result)

    def test_07_not_in(self):
        subdomain = [('id', 'not in', self.children[1:3].ids)]
        domain = [(self.path, 'any', subdomain)]
        self.execute_test(domain, self.get_parents(self.children[0]))


class TestSubfield:
    '''
    This class defines a set of tests where parent records are searched on a
    condition in function of a field of their related records. Between the
    parent and their related records a one2many relationship exists. Different
    records related to the same parent record can still have the same value for
    the field being searched.

    Parent records are created, as part of the class setup, for all possible
    combinations of field values (with repetition) up to a predefined maximum
    number of related records.

    For example, if the values for the searchable field are 1 and 2, and the
    predefined limit is 2, then parents will be created for the following
    combinations of values:
    (), (2), (2, 2), (1), (1, 2), (1, 1)
    '''
    @classmethod
    def prepare_data(cls, params, limit=2):
        cls.params = params
        cls.limit = limit
        cls.path = f'{cls.parent_field}.{cls.child_field}'
        cls.parents = cls.parent_model.create([
            cls.get_parent_values({
                cls.parent_field: [
                    (0, 0, {
                        **cls.get_child_values(param, k),
                        cls.child_field: param,
                    })
                    for index, param in enumerate(params)
                    for k in range(0, counts[index])
                ],
            }, params, counts)
            for counts in cls.combinations()
        ])

    @classmethod
    def combinations(cls):
        return (
            tuple(totals[i] - totals[i - 1] - 1 for i in range(1, len(totals)))
            for totals in ((-1, *offsets) for offsets in combinations(
                range(len(cls.params) + cls.limit), len(cls.params)
            ))
        )

    @classmethod
    def get_parent_values(cls, values, params, counts):
        name = cls.parent_model._name.split('.')[-1]
        return {
            'name': name + ''.join(str(count) for count in counts),
            **values,
        }

    @classmethod
    def get_parents(cls, n=None, m=None):
        return cls.parents.browse([
            cls.parents[index].id
            for index, combination in enumerate(cls.combinations())
            if (n is None or n == combination[0])
            and (m is None or m == combination[1])
        ])

    def test_00_equals_false(self):
        subdomain = [(self.child_field, '=', False)]
        domain = [(self.parent_field, 'any', subdomain)]
        self.execute_test(domain, self.parent_model)

    def test_01_not_equals_false(self):
        subdomain = [(self.child_field, '!=', False)]
        domain = [(self.parent_field, 'any', subdomain)]
        result = self.parents - self.get_parents(n=0, m=0)
        self.execute_test(domain, result)

    def test_02_equals(self):
        subdomain = [(self.child_field, '=', self.params[0])]
        domain = [(self.parent_field, 'any', subdomain)]
        self.execute_test(domain, self.parents - self.get_parents(n=0))

    def test_03_not_equals(self):
        subdomain = [(self.child_field, '!=', self.params[0])]
        domain = [(self.parent_field, 'any', subdomain)]
        self.execute_test(domain, self.parents - self.get_parents(m=0))

    def test_04_all_equals(self):
        subdomain = [(self.child_field, '=', self.params[0])]
        domain = [(self.parent_field, 'all', subdomain)]
        self.execute_test(domain, self.get_parents(m=0))

    def test_05_all_not_equals(self):
        subdomain = [(self.child_field, '!=', self.params[0])]
        domain = [(self.parent_field, 'all', subdomain)]
        self.execute_test(domain, self.get_parents(n=0))


###############################################################################
# Test classes                                                                #
###############################################################################


class TestOne2Many(SearchCase, TestOne2ManyBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.partner']
        cls.parent_field = 'child_ids'
        cls.prepare_data(2)


class TestMany2Many(SearchCase, TestMany2ManyBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.partner.category']
        cls.parent_field = 'partner_ids'
        cls.prepare_data(3)


class TestOne2ManySubfield(SearchCase, TestSubfield):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.partner']
        cls.parent_field = 'child_ids'
        cls.child_field = 'type'
        cls.prepare_data(['invoice', 'delivery'])

    @classmethod
    def get_child_values(cls, param, count):
        return {'name': 'Child partner'}


class TestOne2ManySubfieldWithAutojoin(SearchCase, TestSubfield):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.partner']
        cls.parent_field = 'user_ids'
        cls.child_field = 'signature'
        cls.user_counter = 0
        cls.prepare_data(['<p>Kind regards</p>', '<p>Salutations</p>'])

    @classmethod
    def get_child_values(cls, param, count):
        login = f'user{cls.user_counter}'
        cls.user_counter += 1
        return {'login': login}


class TestMany2ManySubfield(SearchCase, TestSubfield):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.partner.category']
        cls.parent_field = 'partner_ids'
        cls.child_field = 'type'
        cls.prepare_data(['invoice', 'delivery'], 2)
        assert len(cls.parents) == 6

    @classmethod
    def get_child_values(cls, param, count):
        return {'name': 'Test partner'}


class TestMany2One2ManySubfield(SearchCase, TestSubfield):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.users']
        cls.parent_field = 'company_id.child_ids'
        cls.child_field = 'report_header'
        cls.company_counter = 0
        cls.prepare_data(['<p>Company A</p>', '<p>Company B</p>'], 3)
        assert len(cls.parents) == 10

    @classmethod
    def get_child_values(cls, param, count):
        counter = cls.company_counter
        cls.company_counter += 1
        return {'name': 'child_company' + str(counter)}

    @classmethod
    def get_parent_values(cls, values, params, counts):
        commands = values[cls.parent_field]
        path = cls.parent_field.split('.')
        unique_id = ''.join(str(count) for count in counts)
        company = cls.parent_model[path[0]].create({
            'name': 'company' + unique_id,
            path[1]: commands,
        })
        return super().get_parent_values({
            'login': 'user' + unique_id,
            'company_ids': [(4, company.id)],
            path[0]: company.id,
        }, params, counts)


class TestOne2Many2ManySubfield(SearchCase, TestSubfield):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_model = cls.env['res.users']
        cls.parent_field = 'child_ids.child_ids'
        cls.child_field = 'type'
        cls.partner_counter = 0
        cls.prepare_data(['invoice', 'delivery'], 3)
        assert len(cls.parents) == 10

    @classmethod
    def get_child_values(cls, param, count):
        counter = cls.partner_counter
        cls.partner_counter += 1
        return {'name': f'child_partner-{param}-{counter}'}

    @classmethod
    def get_parent_values(cls, values, params, counts):
        # The implementation from the parent class will prefill the parent
        # dictionary with an entry for child_ids.child_ids which we need to
        # convert to an appropriate entry for child_ids.
        path = cls.parent_field.split('.')
        unique_id = ''.join(str(count) for count in counts)
        commands = [(0, 0, {
            'name': command[2]['name'] + '_parent',
            path[1]: [command],
        }) for command in values.pop(cls.parent_field)]
        return super().get_parent_values({
            'login': 'user' + unique_id,
            path[0]: commands,
            **values,
        }, params, counts)
