# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo.tests import TransactionCase, no_retry


# (model, field) holding code that is run through safe_eval.
CODE_FIELDS = (
    ('hr.salary.rule', 'condition_python'),
    ('hr.salary.rule', 'amount_python_compute'),
    ('hr.salary.rule', 'amount_percentage_base'),
    ('hr.salary.rule', 'quantity'),
    ('hr.payroll.warning', 'evaluation_code'),
    ('l10n.be.281.mapping', 'evaluation_value'),
    ('ir.actions.server', 'code'),
    ('ir.model.fields', 'compute'),
    ('gamification.goal.definition', 'compute_code'),
    ('gamification.goal.definition', 'batch_user_expression'),
)


@no_retry
class TestSafeEvalLint(TransactionCase):

    def test_safe_eval_code_has_no_generator_expression(self):
        """ Generator expressions are much slower than list comprehensions in
        safe_eval: forbid them in the code stored in data records.

        safe_eval rewrites each generator expression into a ``_SafeGenerator``
        wrapper whose ``__next__`` calls ``assert_safe_context()`` before and
        after every item.
        """
        env = self.env(context={'active_test': False})
        for model, fname in CODE_FIELDS:
            if model not in env or fname not in env[model]._fields:
                continue
            for record in env[model].search([]):
                code = record[fname]
                if not code or not isinstance(code, str):
                    continue
                tree = ast.parse(code.strip())
                with self.subTest(model=model, record=record.display_name, field=fname):
                    msg = (
                        f"Field {fname} of {model} '{record.display_name}' uses a generator "
                        f"expression. safe_eval checks each item a generator yields, which is slow: "
                        f"use `sum([x for x in ...])`, not `sum(x for x in ...)`.\n{code}"
                    )
                    has_generator_exp = any(isinstance(node, ast.GeneratorExp) for node in ast.walk(tree))
                    if has_generator_exp:
                        self.fail(msg)
