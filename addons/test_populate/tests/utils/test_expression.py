from odoo.tests.common import BaseCase

from odoo.addons.populate.utils.expression import get_undefined_names


class TestGetUndefinedNames(BaseCase):

    def assertUndefinedNames(self, expr, expected):
        self.assertSetEqual(get_undefined_names(expr), expected)

    def test_basic_expressions(self):
        cases = [
            ("a + b", {'a', 'b'}),
            ("record.price * factor", {'record', 'factor'}),
            ("sum(x for x in values)", {'values'}),
            ('f"{name} ({count})"', {'name', 'count'}),
        ]
        for expr, expected in cases:
            with self.subTest(expr=expr):
                self.assertUndefinedNames(expr, expected)

    def test_lambdas(self):
        cases = [
            ('(lambda x: x + price)(1)', {'price'}),
            ('(lambda x=price: x + fee)()', {'price', 'fee'}),
            ('(lambda x, /, y, *args, z=price, **kwargs: x + y + z + fee)(1, 2)', {'price', 'fee'}),
        ]
        for expr, expected in cases:
            with self.subTest(expr=expr):
                self.assertUndefinedNames(expr, expected)

    def test_comprehensions(self):
        cases = [
            ("[x for row in matrix for x in row]", {'matrix'}),
            ("[x * factor for x in items]", {'items', 'factor'}),
            ("{k: v * scale for k, v in pairs}", {'pairs', 'scale'}),
            ("[(head, tail, marker) for head, *tail in rows if marker]", {'rows', 'marker'}),
            ("[x.name for x in obj.records]", {'obj'}),
        ]
        for expr, expected in cases:
            with self.subTest(expr=expr):
                self.assertUndefinedNames(expr, expected)

    def test_named_expressions(self):
        cases = [
            ("(x := field_a)", {'field_a'}),
            ("(x := field_a) and x + 1", {'field_a'}),
            ("(x := x + 1) and x + 6", {'x'}),
            ("field_b if (y := field_a) else y", {'field_a', 'field_b'}),
            ("(a := field_a) and (b := field_b) and a and b", {'field_a', 'field_b'}),
        ]
        for expr, expected in cases:
            with self.subTest(expr=expr):
                self.assertUndefinedNames(expr, expected)

    def test_named_expressions_in_comprehensions(self):
        cases = [
            ("[y := f(x) for x in items]", {'items', 'f'}),
            ("[(z := x) for x in xs if z > threshold]", {'xs', 'z', 'threshold'}),
        ]
        for expr, expected in cases:
            with self.subTest(expr=expr):
                self.assertUndefinedNames(expr, expected)
