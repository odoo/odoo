# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged

from odoo.addons.resource.models.utils import filter_map_domain


@tagged('-at_install', 'post_install')
class TestFilterMapDomain(TransactionCase):
    """
    _filter_map_domain() can filter and map domain
    conditions while still keeping the RPN structure valid.

    This function needs to handle multiple cases for domains:
    - Nested domains
    - Not break due to the internal usage of None
    - Keep the structure as valid RPN, removing some operators if needed

    If everything is filtered out (when the map function returns None for each
    condition), then Domain.TRUE should be returned (which also represents an
    empty domain)

    This test suite will try to ensure all of the above.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.complex_domain = Domain(
            [
                '|',
                    '&',
                        ('overtime_hours', '>=', 2),
                        ('manager_email', 'ilike', 'tecna'),
                    '&',
                        '|',
                            ('department_id', 'in', [4, 5]),
                            ('department_manager', 'ilike', 'Tecna'),
                        '|',
                            '&',
                                ('employee_id', 'in', [1, 2, 3]),
                                ('manager_id', 'ilike', 'Flora'),
                            ('color', '=', 1),
            ],
        )

    def test_translation_only(self):
        def map_function(condition):
            field_expr, operator, value = (
                condition.field_expr,
                condition.operator,
                condition.value,
            )
            field_expr = {
                'overtime_hours': 'extra_mile',
                'department_manager': 'big_boss',
                'color': 'darkness',
            }.get(field_expr, field_expr)
            if operator == '>=':
                operator = '<'
            if not isinstance(value, list):
                value = {
                    'tecna': 'death',
                    'Tecna': 'Death',
                    'Flora': 'Sorrow',
                }.get(value, value)
            return Domain(field_expr, operator, value)

        expected_domain = Domain(
            [
                '|',
                    '&',
                        ('extra_mile', '<', 2),
                        ('manager_email', 'ilike', 'death'),
                    '&',
                        '|',
                            ('department_id', 'in', [4, 5]),
                            ('big_boss', 'ilike', 'Death'),
                        '|',
                            '&',
                                ('employee_id', 'in', [1, 2, 3]),
                                ('manager_id', 'ilike', 'Sorrow'),
                        ('darkness', '=', 1),
            ],
        )
        self.assertEqual(
            expected_domain,
            filter_map_domain(
                self.complex_domain,
                map_function,
            ),
        )

    def test_filter_only(self):
        def map_function(condition):
            if condition.field_expr in [
                'manager_email',
                'color',
                'department_id',
            ]:
                return None
            return condition

        expected_domain = Domain(
            [
                '|',
                    ('overtime_hours', '>=', 2),
                    '&',
                        ('department_manager', 'ilike', 'Tecna'),
                        '&',
                            ('employee_id', 'in', [1, 2, 3]),
                            ('manager_id', 'ilike', 'Flora'),
            ],
        )
        self.assertEqual(
            expected_domain,
            filter_map_domain(
                self.complex_domain,
                map_function,
            ),
        )

    def test_filter_all(self):
        def map_function(condition):
            return None

        expected_domain = Domain.TRUE
        self.assertEqual(
            expected_domain,
            filter_map_domain(
                self.complex_domain,
                map_function,
            ),
        )

    def test_do_nothing(self):
        def map_function(condition):
            if condition.field_expr == 'will_never_exist':
                return None
            return condition

        expected_domain = self.complex_domain
        self.assertEqual(
            expected_domain,
            filter_map_domain(
                self.complex_domain,
                map_function,
            ),
        )

    def test_do_nothing_empty_function(self):
        def map_function(condition):
            return condition

        expected_domain = self.complex_domain
        self.assertEqual(
            expected_domain,
            filter_map_domain(
                self.complex_domain,
                map_function,
            ),
        )

    def test_simple_domain_map(self):
        def map_function(condition):
            if condition.field_expr == 'child_id':
                return Domain('parent_id', condition.operator, condition.value)
            return condition

        # map_domain should convert this list to Domain automatically
        simple_domain = [('child_id', '=', 7)]
        expected_domain = Domain('parent_id', '=', 7)
        self.assertEqual(
            expected_domain,
            filter_map_domain(simple_domain, map_function),
        )

    def test_simple_domain_filter(self):
        def map_function(condition):
            if condition.field_expr == 'child_id':
                return None
            return condition

        # map_domain should convert this list to Domain automatically
        simple_domain = [('child_id', '=', 7)]
        expected_domain = Domain.TRUE
        self.assertEqual(
            expected_domain,
            filter_map_domain(simple_domain, map_function),
        )

    def test_domain_falsy_values(self):
        def map_function(condition):
            field_expr, operator, value = (
                condition.field_expr,
                condition.operator,
                condition.value,
            )
            if value == '':  # noqa: PLC1901
                value = 'so many things'
            if value == False:  # noqa: E712
                value = True
            if operator == 'ilike':
                operator = 'like'
            if field_expr == 'money':
                field_expr = 'problems'
                operator = '<'
                value = 1
            if field_expr == 'cookie':
                return None
            return Domain(field_expr, operator, value)

        domain_with_falsy_values = [
            '&',
                '|',
                    '&',
                        ('cookie', '=', []),
                        ('reason_to_live', '=', None),
                    '&',
                        ('things', 'ilike', ''),
                        ('smile', '=', False),
                ('money', '=', 0),
        ]
        # None will now be true since Domain() converts None to False
        expected_domain = Domain(
            [
                '&',
                    '|',
                        ('reason_to_live', '=', True),
                        '&',
                            ('things', 'like', 'so many things'),
                            ('smile', '=', True),
                    ('problems', '<', 1),
            ],
        )
        self.assertEqual(
            expected_domain,
            filter_map_domain(
                domain_with_falsy_values,
                map_function,
            ),
        )

    def test_swap_fields(self):
        def map_function(condition):
            if condition.field_expr == 'employee_id':
                return Domain('manager_id', condition.operator, condition.value)
            if condition.field_expr == 'manager_id':
                return Domain(
                    'employee_id',
                    condition.operator,
                    condition.value,
                )
            return None

        domain = Domain(
            [
                '|',
                    '&',
                        ('employee_id', 'in', [1, 2, 3]),
                        ('manager_id', '=', 7),
                    '&',
                        ('employee_id', '=', 0),
                        ('manager_id', 'in', [8, 9, 5]),
            ],
        )
        expected_domain = Domain(
            [
                '|',
                    '&',
                        ('manager_id', 'in', [1, 2, 3]),
                        ('employee_id', '=', 7),
                    '&',
                        ('manager_id', '=', 0),
                        ('employee_id', 'in', [8, 9, 5]),
            ],
        )
        self.assertEqual(
            expected_domain,
            filter_map_domain(domain, map_function),
        )

    def test_not_operator(self):
        """
        The not operator is not removed by Domain() when field_expr is dotted
        filter_map_domain thus needs to support not operators.
        """

        def map_function(condition):
            if condition.field_expr == 'c.d':
                return Domain('e.f', condition.operator, condition.value)
            return None

        domain = Domain(
            [
                '|',
                    '!',
                        ('a.b', 'in', [1, 2, 3]),
                    '!',
                        ('c.d', '=', 7),
            ],
        )
        expected_domain = Domain(
            [
                '!',
                    ('e.f', '=', 7),
            ],
        )
        self.assertEqual(
            expected_domain,
            filter_map_domain(domain, map_function),
        )

    def test_filter_domain_leaf_filter(self):
        """
        filter_map_domain() replaces filter_domain_leaf()
        We thus moved the old filter_domain_leaf tests to make sure
        filter_map_domain is backwards compatible
        """
        domains = [
            ['|', ('skills', '=', 1), ('admin', '=', True)],
            [
                '|',
                ('skills', '=', 1),
                ('admin', '=', True),
                '|',
                ('skills', '=', 2),
                ('admin', '=', True),
            ],
            [
                '|',
                ('skills', '=', 1),
                ('skills', '=', 2),
                '|',
                ('skills', '=', 2),
                ('admin', '=', True),
            ],
            [
                '|',
                '|',
                ('skills', '=', 1),
                ('skills', '=', True),
                '|',
                ('skills', '=', 2),
                ('admin', '=', True),
            ],
            [
                '|',
                '|',
                ('admin', '=', 1),
                ('admin', '=', True),
                '&',
                ('skills', '=', 2),
                ('admin', '=', True),
            ],
            [
                '|',
                '|',
                '!',
                ('admin', '=', 1),
                ('admin', '=', True),
                '!',
                '&',
                '!',
                ('skills', '=', 2),
                ('admin', '=', True),
            ],
            ['&', '!', ('skills', '=', 2), ('admin', '=', True)],
            [
                ['start_datetime', '<=', '2022-12-17 22:59:59'],
                ['end_datetime', '>=', '2022-12-10 23:00:00'],
            ],
            [
                ('admin', '=', 1),
                ('admin', '=', 1),
                '|',
                ('admin', '=', 1),
                ('admin', '=', 1),
                ('skills', '=', 2),
            ],
        ]
        fields_to_remove = [['skills'], ['admin', 'skills']]
        expected_results = [
            [
                [('admin', '=', True)],
                [('admin', '=', True), ('admin', '=', True)],
                [('admin', '=', True)],
                [('admin', '=', True)],
                [
                    '|',
                    '|',
                    ('admin', '=', 1),
                    ('admin', '=', True),
                    ('admin', '=', True),
                ],
                [
                    '|',
                    '|',
                    '!',
                    ('admin', '=', 1),
                    ('admin', '=', True),
                    '!',
                    ('admin', '=', True),
                ],
                [('admin', '=', True)],
                [
                    ['start_datetime', '<=', '2022-12-17 22:59:59'],
                    ['end_datetime', '>=', '2022-12-10 23:00:00'],
                ],
                [
                    ('admin', '=', 1),
                    ('admin', '=', 1),
                    '|',
                    ('admin', '=', 1),
                    ('admin', '=', 1),
                ],
            ],
            [
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [
                    ['start_datetime', '<=', '2022-12-17 22:59:59'],
                    ['end_datetime', '>=', '2022-12-10 23:00:00'],
                ],
                [],
            ],
        ]

        for idx, fields in enumerate(fields_to_remove):

            def map_function(condition):
                if condition.field_expr in fields:
                    return None
                return condition

            results = [filter_map_domain(dom, map_function) for dom in domains]
            self.assertEqual(
                results,
                [Domain(expected) for expected in expected_results[idx]],
            )

    # second part from old test_filter_domain_leaf
    def test_filter_domain_leaf_map(self):
        def map_function(condition):
            if condition.field_expr != 'field3':
                return None
            return Domain('field4', condition.operator, condition.value)

        self.assertEqual(
            Domain('field4', '!=', 'test'),
            filter_map_domain(
                [
                    '|',
                        ('field1', 'in', [1, 2]),
                        '!',
                        ('field2', '=', False),
                    ('field3', '!=', 'test'),
                ],
                map_function,
            ),
        )
