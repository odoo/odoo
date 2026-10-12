from odoo.tests.common import BaseCase, TransactionCase, tagged
from odoo.tools.safe_eval import expr_eval


@tagged('at_install', '-post_install')
class TestExprEval(BaseCase):
    def test_basic_arithmetic(self):
        cases = {
            '2 + 3': 5,
            '10 - 3': 7,
            '4 * 5': 20,
            '20 / 4': 5.0,
            '20 // 4': 5,
            '10 % 3': 1,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_operator_precedence(self):
        cases = {
            '2 + 3 * 4': 14,
            '(2 + 3) * 4': 20,
            '10 - 4 / 2': 8.0,
            '(10 - 4) / 2': 3.0,
            '10 % 4 + 1': 3,
            '-2 + 5': 3,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_boolean_logic(self):
        cases = {
            'True and False': False,
            'True or False': True,
            'not True': False,
            'not False': True,
            'True and not False': True,
            'False or not False': True,
            '0 and 1': 0,
            'False or None': None,
            '0 or 1': 1,
            '1 or 0': 1,
            '1 and 0': 0,
            '[] or \'fallback\'': 'fallback',
            '[1] and \'ok\'': 'ok',
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_boolean_short_circuit(self):
        self.assertEqual(expr_eval('False and unknown_variable'), False)
        self.assertEqual(expr_eval('True or unknown_variable'), True)
        self.assertEqual(expr_eval('False and (1 / 0)'), False)
        self.assertEqual(expr_eval('True or (1 / 0)'), True)

    def test_comparisons(self):
        cases = {
            '1 < 2': True,
            '2 > 1': True,
            '2 == 2': True,
            '3 != 4': True,
            '1 <= 1': True,
            '2 >= 3': False,
            '1 < 2 < 3': True,
            '1 < 2 > 3': False,
            '2 == 2 == 2': True,
            '2 == 2 != 3': True,
            '[1] == [1]': True,
            '[1] is [1]': False,
            'None is None': True,
            'None is not None': False,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_min_max_calls(self):
        cases = {
            'min(1, 2)': 1,
            'max(1, 2)': 2,
            'min(3, 2, 1)': 1,
            'max(3, 2, 1)': 3,
            'min([5, 3, 4])': 3,
            'max([5, 3, 4])': 5,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_contains(self):
        cases = {
            '1 in [1, 2, 3]': True,
            '4 in [1, 2, 3]': False,
            '"a" in "cat"': True,
            '"z" not in "cat"': True,
            'b"a" in b"cat"': True,
            'b"z" not in b"cat"': True,
            '2 in (1, 2, 3)': True,
            '4 not in (1, 2, 3)': True,
            '2 in {1, 2, 3}': True,
            '4 in {1, 2, 3}': False,
            '4 not in {1, 2, 3}': True,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_variables(self):
        context = {'x': 10, 'y': 5}
        cases = {
            'x + y': 15,
            'x - y': 5,
            'x * y': 50,
            'x / y': 2.0,
            'x // y': 2,
            'x % y': 0,
            'x is not y': True,
            'x > y': True,
            'x == 10': True,
            'y < 3': False,
            'not x < y': True,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr, context=context), expected)

    def test_list_tuple_dict(self):
        cases = {
            '[1, 2, 3]': [1, 2, 3],
            '(1, 2, 3)': (1, 2, 3),
            '{1, 2, 3}': {1, 2, 3},
            '{}': {},
            'set()': set(),
            'float("-inf")': float('-inf'),
            'float("+inf")': float('+inf'),
            'float("1e-003")': float('1e-003'),
            'float("-Infinity")': float('-Infinity'),
            '{"a": 1, "b": 2}': {'a': 1, 'b': 2},
            '[("name", "=", "x")]': [('name', '=', 'x')],
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr), expected)

    def test_subscripts(self):
        context = {
            'vals': {'amount': 42, 'items': [10, 20, 30]},
            'lines': [
                {'balance': 100},
                {'balance': 200},
            ],
        }
        cases = {
            'vals["amount"]': 42,
            'vals["items"][1]': 20,
            'lines[0]["balance"]': 100,
            'lines[1]["balance"] > lines[0]["balance"]': True,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr, context=context), expected)

    def test_domains(self):
        context = {
            'user_id': 7,
            'group_ids': [1, 2, 3],
        }
        cases = {
            '[("user_id", "=", user_id)]': [('user_id', '=', 7)],
            '[("group_ids", "in", group_ids)]': [('group_ids', 'in', [1, 2, 3])],
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr, context=context), expected)

    def test_unknown_variable(self):
        with self.assertRaises(NameError):
            expr_eval('missing + 1')

    def test_runtime_errors_are_not_hidden(self):
        with self.assertRaises(ZeroDivisionError):
            expr_eval('1 / 0')

        with self.assertRaises(IndexError):
            expr_eval('[1][5]')

        with self.assertRaises(KeyError):
            expr_eval('{}["x"]')

    def test_invalid_expressions(self):
        for expr, exc in (
            ('2 +', SyntaxError),
            ('* 3', SyntaxError),
            ('import os', SyntaxError),
            ('a.b', NameError),
            ('unknown_func()', NameError),
            ('a.b = c', SyntaxError),
        ):
            with self.subTest(expr=expr):
                with self.assertRaises(exc):
                    expr_eval(expr)

    def test_unsupported_constants(self):
        for expr in ('...', '1j'):
            with self.subTest(expr=expr):
                with self.assertRaises(TypeError):
                    expr_eval(expr)

    def test_no_cache_mutables(self):
        mutable_lst = expr_eval("[]")
        mutable_lst.append(1)
        self.assertNotIn(1, expr_eval("[]"))

        mutable_ctx = {'a': [1, 2]}
        res1 = expr_eval('a[0] + a[1]', mutable_ctx)
        self.assertEqual(res1, 3)

        mutable_ctx['a'][0] = 2
        res2 = expr_eval('a[0] + a[1]', mutable_ctx)
        self.assertEqual(res2, 4)


class TestExprEvalAttribute(TransactionCase):
    def test_attribute(self):
        user = self.env.user
        context = {
            'user': user,
            's': "hello",
        }
        cases = {
            'user.id': user.id,
            'user.ids': user.ids,
            'user._name + s': user._name + "hello",
            'user.login': user.login,
            'user.company_ids[:1].name': user.company_ids[:1].name,
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(expr_eval(expr, context=context), expected)

        for expr in (
            'user.login.islower',
            'user.env',
            'user.new()',
            's.lower',
        ):
            with self.subTest(expr=expr), self.assertRaises(Exception):
                expr_eval(expr, context=context)
