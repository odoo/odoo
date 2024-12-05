from freezegun import freeze_time

from odoo.addons.mass_mailing.models.mailing_filter import MailingFilter
from odoo.exceptions import UserError
from odoo.tests import BaseCase
from odoo.tools import mute_logger


class TestDynamicDomainHelpers(BaseCase):

    @mute_logger('odoo.tools.translate')
    def test_domain_combination(self):
        combine = MailingFilter._combine_dynamic_domains
        failing_triplets = [
            (False, False, TypeError),
            ('', '', UserError),
            ('[]', '', UserError),
            ('["&", (1, "=", 1)', '[]', UserError),  # unmatched hook, python syntax error
            ([], '[]', TypeError),
            ('list()', '[]', UserError),  # the first one is not syntactically a list
        ]
        for domain_a, domain_b, exception in failing_triplets:
            with self.subTest(domain_a=domain_a, domain_b=domain_b):
                with self.assertRaises(exception):
                    combine(domain_a, domain_b)

        success_triplets = [
            ('[]', '[]', '[]'),
            ('[]', '[(1, "=", 1)]', "[(1, '=', 1)]"),
            ('[(1, "!=", 0)]', '[(0, "!=", 1)]', "['&', (1, '!=', 0), (0, '!=', 1)]"),
            (
                '["|", ("name", "like", "_bob%"), ("rating", ">", 3)]',
                '["|", ("rating", "<", 6), ("name", "like", "a%")]',
                "['&', '|', ('name', 'like', '_bob%'), ('rating', '>', 3), '|', ('rating', '<', 6), ('name', 'like', 'a%')]",
            ),
            (
                '[("create_date", "<", context_today())]',
                '[("create_date", "<", context_today() - relativedelta(days=1))]',
                "['&', ('create_date', '<', context_today()), ('create_date', '<', context_today() - relativedelta(days=1))]",
            ),
            (
                '[1,object,"string"]',
                '[int,int(1),isinstance,lambda x: x + 1]',
                "['&', 1, object, 'string', int, int(1), isinstance, lambda x: x + 1]",
            ),  # it will actually merge any list of expressions
        ]
        for domain_a, domain_b, expected in success_triplets:
            with self.subTest(domain_a=domain_a, domain_b=domain_b, expected=expected):
                self.assertEqual(combine(domain_a, domain_b), expected)

    @freeze_time('2030-05-24')
    @mute_logger('odoo.tools.translate')
    def test_domain_evaluation(self):
        evaluate = MailingFilter._evaluate_domain
        failing_domains = [
            ("()", AssertionError),  # has to be a list
            ("'[]'", AssertionError),
            ("[(1, '=', 1/0)]", ZeroDivisionError),
            ("['name', 'like', datetime.__file__]", NameError),  # basic safety checks, should be raised by safe_eval
            ("import os; ['name', 'like', os.getenv('USER')]", SyntaxError),
        ]
        for domain_expression, exception in failing_domains:
            with self.subTest(domain_expression=domain_expression):
                with self.assertRaises(exception):
                    evaluate(domain_expression)

        success_pairs = [
            ("list()", []),
            ("list(range(1, 4))", [1, 2, 3]),
            ("['|', (1, '=', 1), (1, '>', 0)]", ['|', (1, '=', 1), (1, '>', 0)]),
            ("[(2, '=', 1 + 1)]", [(2, '=', 2)]),
            (
                "[('create_date', '<', datetime.datetime.combine(context_today() - relativedelta(days=100), datetime.time(1, 2, 3)).to_utc().strftime('%Y-%m-%d %H:%M:%S'))]",
                [('create_date', '<', "2030-02-13 01:02:03")],
            ),  # use the date utils used by front-end domains
        ]
        for domain_expression, domain_value in success_pairs:
            with self.subTest(domain_expression=domain_expression, domain_value=domain_value):
                self.assertEqual(evaluate(domain_expression), domain_value)
