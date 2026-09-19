import ast
from pathlib import Path
from textwrap import dedent

from odoo.modules import Manifest
from odoo.tests.common import BaseCase, no_retry

from . import (
    _checker_batch,
    _checker_config_patch,
    _checker_credential_storage,
    _checker_egress,
    _checker_field_declaration,
    _checker_gettext,
    _checker_http_json,
    _checker_noqa_rationale,
    _checker_onchange,
    _checker_orm_import,
    _checker_receiver,
    _checker_shadowed_def,
    _checker_sql,
    _checker_tax_company,
    _checker_unlink,
    _pretty_xml,
    _py_scan,
    _rules,
    _suppression,
    lint_case,
)


def is_suppressed(source: str, lineno: int, rule: str) -> bool:
    return _suppression.Suppressions.of(
        source, _rules.ALIASES, _rules.UNSUPPRESSABLE
    ).suppresses(lineno, rule)


@no_retry
class TestSuppression(BaseCase):
    def test_bare_noqa_suppresses_everything(self):
        self.assertTrue(is_suppressed("x  # noqa", 1, "sql-injection"))

    def test_rationale_does_not_cancel_the_suppression(self):
        for line in (
            "x  # noqa  because the column name is a legacy alias",
            "x  # noqa: E8501 -- table name comes from _table",
            "x  # noqa: E8501, F401  re-exported by __init__",
        ):
            with self.subTest(line=line):
                self.assertTrue(
                    is_suppressed(line, 1, "sql-injection"),
                    "explaining a suppression must not undo it",
                )

    def test_codes_scope_the_suppression(self):
        self.assertFalse(
            is_suppressed("x  # noqa: F401  unused", 1, "sql-injection"),
            "an unrelated code must not silence this rule",
        )

    def test_rule_name_and_numeric_alias_are_equivalent(self):
        for code in ("E8507", "e8507", "n-plus-one-query"):
            with self.subTest(code=code):
                self.assertTrue(
                    is_suppressed(
                        f"x  # noqa: {code}  hoisting needs a schema change",
                        1,
                        "n-plus-one-query",
                    )
                )

    def test_no_two_rules_share_a_code(self):
        by_code = {}
        for rule in _rules.RULES:
            if rule.code:
                by_code.setdefault(rule.code, []).append(rule.name)
        shared = {code: names for code, names in by_code.items() if len(names) > 1}
        self.assertFalse(shared, "a noqa naming the code would silence both rules")

    def test_a_rule_named_in_full_scopes_the_suppression_too(self):
        line = "x  # noqa: sql-injection  the table name comes from _table"
        self.assertTrue(is_suppressed(line, 1, "sql-injection"))
        self.assertFalse(
            is_suppressed(line, 1, "n-plus-one-query"),
            "naming one rule must not waive the others on the line",
        )

    def test_an_unparseable_code_list_silences_nothing(self):
        self.assertFalse(is_suppressed("x  # noqa: !!!  see above", 1, "sql-injection"))

    def test_case_does_not_decide_whether_a_suppression_works(self):
        line = "x  # NOQA: E8501  the table name comes from _table"
        self.assertTrue(is_suppressed(line, 1, "sql-injection"))
        self.assertFalse(_violations(line))
        self.assertTrue(
            is_suppressed("x  # PYLINT: disable=sql-injection", 1, "sql-injection")
        )

    def test_a_directive_only_counts_where_python_sees_a_comment(self):
        for source in (
            'cr.execute("select # noqa from t")',
            "URL = 'http://example.test/#noqa'",
            'SNIPPET = """\n# noqa: E8501\n"""',
        ):
            with self.subTest(source=source):
                self.assertFalse(
                    is_suppressed(source, 1, "sql-injection"),
                    "a directive inside a string literal is not a directive",
                )

    def test_noqa_has_to_be_the_whole_word(self):
        for line in ("x  # noqawhatever", "x  # noqa-ish", "x  # NOQA_TODO"):
            with self.subTest(line=line):
                self.assertFalse(
                    is_suppressed(line, 1, "sql-injection"),
                    "a word merely starting with noqa is not a bare suppression",
                )
        self.assertTrue(is_suppressed("x  # noqa", 1, "sql-injection"))

    def test_a_directive_after_another_comment_still_counts(self):
        self.assertTrue(
            is_suppressed("x  # type: ignore  # noqa: E8501", 1, "sql-injection")
        )


def _violations(source):
    return list(
        _checker_noqa_rationale.find_violations(_suppression.comment_lines(source))
    )


@no_retry
class TestNoqaRationale(BaseCase):
    def _violations(self, line):
        return _violations(line)

    def test_a_rule_name_is_not_its_own_rationale(self):
        self.assertTrue(self._violations("x  # noqa: E8501"))
        self.assertTrue(
            self._violations("x  # noqa: sql-injection"),
            "naming the rule is not a reason for waiving it",
        )
        self.assertTrue(self._violations("x  # noqa: sql-injection, E8507"))

    def test_a_real_rationale_still_passes(self):
        for line in (
            "x  # noqa: E8501  the table name comes from _table",
            "x  # noqa: sql-injection  the table name comes from _table",
            "x  # noqa  the column is a legacy alias",
        ):
            with self.subTest(line=line):
                self.assertFalse(self._violations(line))

    def test_both_spellings_agree_with_the_suppression_module(self):
        for line in ("x  # noqa: E8501", "x  # noqa: sql-injection", "x  # noqa"):
            with self.subTest(line=line):
                self.assertTrue(
                    is_suppressed(line, 1, "sql-injection"),
                    "this line silences the rule",
                )
                self.assertTrue(
                    self._violations(line),
                    "so it has to be asked for a reason",
                )

    def test_pylint_disable_is_still_honoured(self):
        self.assertTrue(
            is_suppressed("x  # pylint: disable=sql-injection", 1, "sql-injection")
        )

    def test_the_rationale_rule_cannot_silence_itself(self):
        self.assertFalse(is_suppressed("x  # noqa", 1, "noqa-rationale"))


@no_retry
class TestCorePathScoping(BaseCase):
    def test_a_sibling_checkout_is_not_core(self):
        root = lint_case.core_root()
        self.assertTrue(lint_case.is_core_path(root))
        self.assertTrue(lint_case.is_core_path(str(Path(root) / "addons" / "x.py")))
        for sibling in (f"{root}-companion", f"{root}_legacy", f"{root}2"):
            with self.subTest(sibling=sibling):
                self.assertFalse(
                    lint_case.is_core_path(str(Path(sibling) / "x.py")),
                    "a separately-versioned checkout is not this repository",
                )

    def test_the_real_siblings_on_this_addons_path_are_excluded(self):
        roots = [manifest.path for manifest in Manifest.get_all_addon_manifests()]
        self.assertTrue(roots, "no addon roots at all")
        core = [path for path in roots if lint_case.is_core_path(str(path))]
        self.assertTrue(core, "no core addon roots -- the scoping reached nothing")
        self.assertTrue(
            all(Path(lint_case.core_root()) in Path(path).parents for path in core),
            "is_core_path admitted a root outside this repository",
        )


@no_retry
class TestScanScope(BaseCase):
    def test_a_data_file_is_xml(self):
        from pathlib import Path

        self.assertTrue(_pretty_xml.is_formattable(Path("/a/account/views/x.xml")))
        for path in ("/a/account/views/x.py", "/a/account/README.md"):
            with self.subTest(path=path):
                self.assertFalse(_pretty_xml.is_formattable(Path(path)))

    def test_the_shared_data_file_selection_is_reused_not_rebuilt(self):
        self.assertIs(lint_case._core_data_files(), lint_case._core_data_files())
        self.assertIsNot(
            lint_case.core_data_files(),
            lint_case.core_data_files(),
            "callers get their own list; the cache holds an immutable tuple",
        )

    def test_this_repositorys_modules_are_a_subset_of_the_addons_path(self):
        names = lint_case.core_module_names()
        self.assertIn("base", names)
        self.assertIn("web", names)
        self.assertTrue(
            names <= {m.name for m in Manifest.get_all_addon_manifests()},
            "core modules must be modules the addons path actually carries",
        )


@no_retry
class TestLeadingIndexColumns(BaseCase):
    class _FakeModel:
        pool = None

        def __init__(self, table_objects):
            self._table_objects = table_objects

    def _columns(self, *definitions, unique=False):
        from odoo.orm import models as orm_models

        from .test_index import leading_index_columns

        build = orm_models.UniqueIndex if unique else orm_models.Index
        return leading_index_columns(
            self._FakeModel(
                {str(i): build(definition) for i, definition in enumerate(definitions)}
            )
        )

    def test_a_composite_index_answers_its_leading_column(self):
        self.assertEqual(self._columns("(product_id, location_id)"), {"product_id"})
        self.assertEqual(
            self._columns("(product_id, location_id, lot_id, package_id)"),
            {"product_id"},
        )

    def test_a_trailing_column_is_not_answered(self):
        self.assertNotIn("location_id", self._columns("(product_id, location_id)"))

    def test_a_sort_direction_changes_nothing(self):
        self.assertEqual(self._columns("(date desc, move_name desc, id)"), {"date"})

    def test_a_not_null_partial_index_counts(self):
        self.assertEqual(
            self._columns("(user_id) WHERE user_id IS NOT NULL"), {"user_id"}
        )

    def test_any_other_partial_index_does_not(self):
        for definition in (
            "(channel) WHERE state = 'started'",
            "(id) WHERE state = 'outgoing'",
            "(channel_id, end_dt) WHERE end_dt IS NULL",
            "(has_crm_lead) WHERE has_crm_lead IS TRUE",
        ):
            with self.subTest(definition=definition):
                self.assertEqual(
                    self._columns(definition),
                    set(),
                    "a partial index only answers the rows it covers",
                )

    def test_a_non_btree_index_does_not_answer_equality(self):
        self.assertEqual(self._columns("USING gin (barcode jsonb_path_ops)"), set())

    def test_an_expression_index_has_no_leading_column(self):
        self.assertEqual(self._columns("(lower(name))"), set())

    def test_a_unique_index_counts_like_any_other(self):
        self.assertEqual(
            self._columns("(guest_id) WHERE guest_id IS NOT NULL", unique=True),
            {"guest_id"},
        )


@no_retry
class TestOrmImportLint(BaseCase):
    def _check(self, snippet, filepath="models/thing.py"):
        return list(_checker_orm_import.check(ast.parse(dedent(snippet).strip())))

    def test_direct_import_flagged(self):
        self.assertTrue(self._check("import odoo.orm.fields"))
        self.assertTrue(self._check("from odoo.orm import fields"))
        self.assertTrue(self._check("from odoo.orm.fields import Many2one"))

    def test_facade_import_allowed(self):
        self.assertFalse(self._check("from odoo import api, fields, models"))
        self.assertFalse(self._check("import odoo.ormsomething"))

    def test_string_mentioning_odoo_orm_is_not_an_import(self):
        self.assertFalse(self._check("DOC = 'see odoo.orm.fields for details'"))

    def test_a_type_checking_import_is_not_a_runtime_dependency(self):
        for guard in ("TYPE_CHECKING", "typing.TYPE_CHECKING"):
            with self.subTest(guard=guard):
                self.assertFalse(
                    self._check(f"""
                    if {guard}:
                        from odoo.orm.query import Query
                        import odoo.orm.fields
                    """)
                )

    def test_the_else_branch_of_a_type_checking_block_still_counts(self):
        self.assertTrue(
            self._check("""
            if TYPE_CHECKING:
                from odoo.orm.query import Query
            else:
                from odoo.orm.query import Query
            """)
        )

    def test_a_negated_guard_is_the_runtime_branch(self):
        self.assertTrue(
            self._check("""
            if not TYPE_CHECKING:
                from odoo.orm.query import Query
            """)
        )

    def test_the_exemption_reaches_a_nested_import(self):
        self.assertFalse(
            self._check("""
            if TYPE_CHECKING:
                try:
                    from odoo.orm.query import Query
                except ImportError:
                    Query = object
            """)
        )

    def test_an_unguarded_import_beside_a_guarded_one_is_still_flagged(self):
        self.assertTrue(
            self._check("""
            import odoo.orm.fields

            if TYPE_CHECKING:
                from odoo.orm.query import Query
            """)
        )


@no_retry
class TestConfigChainmapPatchLint(BaseCase):
    def _check(self, snippet):
        return list(_checker_config_patch.check(ast.parse(dedent(snippet).strip())))

    def test_the_attribute_chain_does_not_matter(self):
        for target in (
            "config.options",
            "tools.config.options",
            "odoo.tools.config.options",
            "db_mod.lifecycle.odoo.tools.config.options",
        ):
            self.assertTrue(
                self._check(f'patch.dict({target}, {{"list_db": True}})'),
                target,
            )

    def test_qualified_patch_is_flagged_too(self):
        self.assertTrue(self._check('mock.patch.dict(config.options, {"a": 1})'))
        self.assertTrue(
            self._check('unittest.mock.patch.dict(config.options, {"a": 1})')
        )

    def test_the_replacement_is_not_flagged(self):
        self.assertFalse(self._check("config.patch(list_db=True)"))
        self.assertFalse(self._check("odoo.tools.config.patch(test_tags=tags)"))

    def test_a_plain_dict_is_not_flagged(self):
        self.assertFalse(self._check('patch.dict(config._runtime_options, {"a": 1})'))
        self.assertFalse(self._check('patch.dict(os.environ, {"A": "1"})'))
        self.assertFalse(self._check('patch.dict(self.registry.options, {"a": 1})'))

    def test_patch_object_is_a_different_thing(self):
        self.assertFalse(self._check('patch.object(config, "options", {})'))


@no_retry
class TestOnchangeLint(BaseCase):
    def _check(self, snippet):
        return list(_checker_onchange.check(ast.parse(dedent(snippet).strip())))

    def test_domain_in_onchange_flagged(self):
        self.assertTrue(
            self._check("""
        @api.onchange('partner_id')
        def _onchange_partner(self):
            return {'domain': {'x': []}}
        """)
        )

    def test_a_field_named_domain_is_not_a_dynamic_domain(self):
        self.assertFalse(
            self._check("""
        @api.onchange('a')
        def _onchange_a(self):
            self.env['x'].search([('domain', '=', self.domain)])
        """),
            "a domain leaf naming a field is not a returned {'domain': ...}",
        )

    def test_a_returned_mapping_is_still_flagged(self):
        self.assertTrue(
            self._check("""
        @api.onchange('a')
        def _onchange_a(self):
            result = {'domain': {'x': []}}
            return result
        """),
            "the mapping does not have to be returned inline",
        )

    def test_domain_outside_onchange_ignored(self):
        self.assertFalse(
            self._check("""
        def _compute_something(self):
            return {'domain': {'x': []}}
        """)
        )

    def test_one_report_per_method(self):
        self.assertEqual(
            len(
                self._check("""
            @api.onchange('a')
            def _onchange_a(self):
                x = {'domain': []}
                y = {'domain': []}
                return {'domain': []}
            """)
            ),
            1,
        )


@no_retry
class TestSqlLint(BaseCase):
    def _check(self, snippet, filepath="dummy.py"):
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        nodes = _py_scan.walk_with_parents(tree)
        return list(_checker_sql.SqlInjectionChecker(filepath).check_nodes(nodes))

    def test_a_helper_used_many_times_is_one_finding(self):
        violations = self._check("""
        def a(self, t):
            self.env.cr.execute(build(t))

        def b(self, t):
            self.env.cr.execute(build(t))

        def c(self, t):
            self.env.cr.execute(build(t))

        def build(table):
            return f"SELECT * FROM {table}"
        """)
        self.assertEqual(len(violations), 1, "one helper, one finding")
        for line in ("2", "5", "8"):
            self.assertIn(f"dummy.py:{line}", violations[0].message)

    def test_a_same_named_method_in_another_class_does_not_taint_a_safe_one(self):
        violations = self._check("""
        class A:
            def _query(self):
                return "select 1"

        class B:
            def _query(self):
                return "select " + user_input

        class C:
            def run(self):
                self.env.cr.execute(A()._query())
        """)
        self.assertFalse(
            violations, "A's safe method must not be flagged over B's unsafe one"
        )

    def test_a_helper_defined_first_is_reported_at_each_call(self):
        violations = self._check("""
        def build(table):
            return f"SELECT * FROM {table}"

        def a(self, t):
            self.env.cr.execute(build(t))

        def b(self, t):
            self.env.cr.execute(build(t))
        """)
        self.assertEqual(len(violations), 2)
        self.assertEqual(sorted(v.lineno for v in violations), [5, 8])

    def test_two_queries_on_one_line_are_two_findings(self):
        violations = self._check(
            "def f(self, a, b):\n"
            '    self.env.cr.execute(f"S {a}"), self.env.cr.execute(f"S {b}")\n'
        )
        self.assertEqual(len(violations), 2)
        self.assertEqual(violations[0].lineno, violations[1].lineno)
        self.assertNotEqual(violations[0].col_offset, violations[1].col_offset)

    def test_a_local_constant_is_resolved_through_its_scope(self):
        self.assertFalse(
            self._check("""
        def f(self):
            tbl = "things"
            self.env.cr.execute("SELECT * FROM %s" % tbl)
        """),
            "the name resolves to a literal; reporting it needs `_parent` set",
        )

    def test_printf(self):
        violations = self._check("""
        def do_the_thing(cr, name):
            cr.execute('select %s from thing' % name)
        """)
        self.assertTrue(violations, "should have noticed the injection")
        self.assertEqual(violations[0].lineno, 2)

        violations = self._check("""
        def do_the_thing(self):
            self.env.cr.execute("select thing from %s" % self._table)
        """)
        self.assertFalse(violations, "underscore-attributes are allowed")

        violations = self._check("""
        def do_the_thing(self):
            query = "select thing from %s"
            self.env.cr.execute(query % self._table)
        """)
        self.assertFalse(violations, "underscore-attributes are allowed")

    def test_fstring(self):
        violations = self._check("""
        def do_the_thing(cr, name):
            cr.execute(f'select {name} from thing')
        """)
        self.assertTrue(violations, "should have noticed the injection")
        self.assertEqual(violations[0].lineno, 2)

        violations = self._check("""
        def do_the_thing(cr, name):
            cr.execute(f'select name from thing')
        """)
        self.assertFalse(violations, "unnecessary fstring should be innocuous")

        violations = self._check("""
        def do_the_thing(self):
            self.env.cr.execute(f'select name from {self._table}')
        """)
        self.assertFalse(violations, "underscore-attributes are allowable")

    def test_const_concat(self):
        violations = self._check("""
        def test():
            arg = "test"
            arg = arg + arg
            self.env.cr.execute(arg)
        """)
        self.assertFalse(violations)

    def test_percent_with_param(self):
        violations = self._check("""
        def test_function9(self, arg):
            my_injection_variable = "aaa" % arg
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_const_plus_const(self):
        violations = self._check("""
        def test_function10(self):
            my_injection_variable = "aaa" + "aaa"
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_const_plus_arg(self):
        violations = self._check("""
        def test_function11(self, arg):
            my_injection_variable = "aaaaaaaa" + arg
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_transitive_const_chain(self):
        violations = self._check("""
        def test_function12(self):
            arg1 = "a"
            arg2 = "b" + arg1
            arg3 = arg2 + arg1 + arg2
            arg4 = arg1 + "d"
            my_injection_variable = arg1 + arg2 + arg3 + arg4
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_fstring_with_param(self):
        violations = self._check("""
        def test_function1(self, arg):
            my_injection_variable = f"aaaaa{arg}aaa"
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_fstring_with_const_var(self):
        violations = self._check("""
        def test_function2(self):
            arg = 'bbb'
            my_injection_variable = f"aaaaa{arg}aaa"
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_no_args(self):
        violations = self._check("""
        def test_function3(self, arg):
            my_injection_variable = "aaaaaaaa".format()
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_keyword_const(self):
        violations = self._check("""
        def test_function4(self, arg):
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa")
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_keyword_const_var(self):
        violations = self._check("""
        def test_function5(self):
            arg = 'aaa'
            my_injection_variable = "aaaaaaaa {test}".format(test=arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_keyword_nonconst(self):
        violations = self._check("""
        def test_function6(self, arg):
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa" + arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_format_keyword_const_chain(self):
        violations = self._check("""
        def test_function7(self):
            arg = "aaa"
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa" + arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_global_var(self):
        violations = self._check("""
        def test_function8(self):
            global arg
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa" + arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_ternary_const_branches(self):
        violations = self._check("""
        def test_function10(self, arg):
            if_else_variable = "aaa" if arg else "bbb"
            self.env.cr.execute('select * from hello where id = %s' % if_else_variable)
        """)
        self.assertFalse(violations)

    def test_a_private_method_is_not_a_licence(self):
        snippet = """
        def {name}(self, user_input):
            self.env.cr.execute("SELECT * FROM t WHERE x = '%s'" % user_input)
        """
        self.assertTrue(self._check(snippet.format(name="do_thing")))
        self.assertTrue(
            self._check(snippet.format(name="_do_thing")),
            "a leading underscore is a naming convention, not a safety proof",
        )

    def test_an_identifier_from_self_is_still_allowed(self):
        self.assertFalse(
            self._check("""
        def _init_column(self, value):
            query = f'UPDATE "{self._table}" SET "{self._rec_name}" = %s'
            self.env.cr.execute(query, (value,))
        """)
        )

    def test_real_false_positive_private_function(self):
        violations = self._check("""
        def _search_phone_mobile_search(self, operator, value):
            condition = 'IS NULL' if operator == '=' else 'IS NOT NULL'
            query = '''
                SELECT model.id
                FROM %s model
                WHERE model.phone %s
                AND model.mobile %s
            ''' % (self._table, condition, condition)
            self.env.cr.execute(query)
        """)
        self.assertFalse(violations)

    def test_tuple_assignment(self):
        violations = self._check("""
        def test1(self):
            operator = 'aaa'
            value = 'bbb'
            op1, val1 = (operator, value)
            self.env.cr.execute('query' + op1)
        """)
        self.assertFalse(violations)

    def test_augassign_const(self):
        violations = self._check("""
        def test2(self):
            operator = 'aaa'
            operator += 'bbb'
            self.env.cr.execute('query' + operator)
        """)
        self.assertFalse(violations)

    def test_fstring_self_table(self):
        violations = self._check("""
        def test3(self):
            self.env.cr.execute(f'{self._table}')
        """)
        self.assertFalse(violations)

    def test_private_function_fstring_with_param(self):
        violations = self._check("""
        def _init_column(self, column_name):
            query = f'UPDATE "{self._table}" SET "{column_name}" = %s WHERE "{column_name}" IS NULL'
            self.env.cr.execute(query, (value,))
        """)
        self.assertTrue(violations)

    def test_a_self_referential_accumulation_terminates(self):
        violations = self._check("""
        def _build(self, where_sql, pids):
            where_clause = where_sql
            if pids:
                where_clause = "(%s) AND (%s)" % (where_clause, "fol.partner_id = ANY(%s)")
            self.env.cr.execute("SELECT id FROM t WHERE " + where_clause)
        """)
        self.assertTrue(
            violations, "an accumulation seeded by a parameter is not a constant"
        )

    def test_an_accumulation_of_constants_stays_constant(self):
        violations = self._check("""
        def _get_seen_list(self):
            target = self.env[self.mailing_model_real]
            query = "SELECT s.email FROM mailing_trace s JOIN %(target)s t ON (s.res_id = t.id)"
            if self.ab_testing_enabled:
                query += " AND s.campaign_id = %%(mailing_campaign_id)s"
            else:
                query += " AND s.mass_mailing_id = %%(mailing_id)s"
            query = query % {"target": target._table}
            self.env.cr.execute(query, {"mailing_id": self.id})
        """)
        self.assertFalse(violations, "every binding of query is a constant or _table")

    def test_a_parameter_appended_to_a_constant_is_not_a_constant(self):
        violations = self._check("""
        def _read(self, table):
            query = "SELECT id FROM "
            query += table
            self.env.cr.execute(query)
        """)
        self.assertTrue(
            violations,
            "resolving the name to its first assignment hid every later binding",
        )

    def test_the_query_passed_by_keyword_is_still_the_query(self):
        violations = self._check("""
        def _read(self, table):
            self.env.cr.execute(query=f"SELECT id FROM {table}")
        """)
        self.assertTrue(violations)

    def test_dict_format_const(self):
        violations = self._check("""
        def _init_column1(self, column_name):
            query = 'SELECT %(var1)s FROM %(var2)s WHERE %(var3)s' % {'var1': 'field_name', 'var2': 'table_name', 'var3': 'where_clause'}
            self.env.cr.execute(query)
        """)
        self.assertFalse(violations)

    def test_complex_private_function(self):
        violations = self._check("""
        def _graph_data(self, start_date, end_date):
            query = '''SELECT %(x_query)s as x_value, %(y_query)s as y_value
                        FROM %(table)s
                        WHERE team_id = %(team_id)s
                        AND DATE(%(date_column)s) >= %(start_date)s
                        AND DATE(%(date_column)s) <= %(end_date)s
                        %(extra_conditions)s
                        GROUP BY x_value;'''
            dashboard_graph_model = self._graph_get_model()
            GraphModel = self.env[dashboard_graph_model]
            graph_table = self._graph_get_table(GraphModel)
            extra_conditions = self._extra_sql_conditions()
            where_query = GraphModel._search([])
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            if where_clause:
                extra_conditions += " AND " + where_clause
            query = query % {
                'x_query': self._graph_x_query(),
                'y_query': self._graph_y_query(),
                'table': graph_table,
                'team_id': "%s",
                'date_column': self._graph_date_column(),
                'start_date': "%s",
                'end_date': "%s",
                'extra_conditions': extra_conditions,
            }
            self.env.cr.execute(query, [self.id, start_date, end_date] + where_clause_params)
            return self.env.cr.dictfetchall()
        """)
        self.assertFalse(violations)

    def test_cross_function_const_return(self):
        violations = self._check("""
        def first_fun():
            return 'a'

        def injectable():
            cr.execute(first_fun())
        """)
        self.assertFalse(violations)

    def test_cross_function_param_with_const_call(self):
        violations = self._check("""
        def second_fun(value):
            return value

        def injectable1():
            cr.execute(second_fun('aaaaa'))
        """)
        self.assertFalse(violations)

    def test_join_const_list(self):
        violations = self._check("""
        def injectable2(var):
            a = ['a', 'b']
            cr.execute('a'.join(a))
        """)
        self.assertFalse(violations)

    def test_cross_function_tuple_position(self):
        violations = self._check("""
        def return_tuple(var):
            return 'a', var

        def injectable4(var):
            a, _ = return_tuple(var)
            cr.execute(a)
        """)
        self.assertFalse(violations)

    def test_starred_const_tuple(self):
        violations = self._check("""
        def not_injectable5(var):
            star = ('defined', 'constant', 'string')
            cr.execute(*star)
        """)
        self.assertFalse(violations)

    def test_starred_nonconst_tuple(self):
        violations = self._check("""
        def injectable6(var):
            star = ('defined', 'variable', 'string', var)
            cr.execute(*star)
        """)
        self.assertTrue(violations)

    def test_percent_d_format(self):
        violations = self._check("""
        def formatNumber(var):
            cr.execute('LIMIT %d' % var)
        """)
        self.assertFalse(violations)

    def test_sql_call_with_variable(self):
        violations = self._check("""
        def wrapper1(var):
            query = SQL(var)
            return query
        """)
        self.assertTrue(violations)

    def test_tools_sql_call_with_variable(self):
        violations = self._check("""
        def wrapper2(var):
            query = tools.SQL(var)
            return query
        """)
        self.assertTrue(violations)

    def test_an_assert_over_the_name_clears_it(self):
        violations = self._check("""
        def build(coltype):
            assert coltype in TYPES
            return SQL(coltype)
        """)
        self.assertFalse(violations, "the assert proves the token is one of a set")

    def test_a_raising_guard_over_the_name_clears_it(self):
        violations = self._check("""
        def create_column(cr, columntype):
            if not _SQL_TYPE_TOKEN.fullmatch(columntype):
                raise ValueError(columntype)
            cr.execute(SQL(columntype))
        """)
        self.assertFalse(
            violations,
            "an `if <bad>: raise` guard proves as much as an assert, and is the "
            "form production code has to use",
        )

    def test_a_guard_that_does_not_raise_clears_nothing(self):
        violations = self._check("""
        def create_column(cr, columntype):
            if columntype == "BOOLEAN":
                columntype = "bool"
            cr.execute(SQL(columntype))
        """)
        self.assertTrue(violations, "a branch that does not raise is not a guard")

    def test_a_guard_over_another_name_clears_nothing(self):
        violations = self._check("""
        def create_column(cr, tablename, columntype):
            if not tablename:
                raise ValueError(tablename)
            cr.execute(SQL(columntype))
        """)
        self.assertTrue(violations, "the guard has to name the value being built")

    def test_every_cursor_spelling_is_recognised(self):
        snippet = """
        def do_the_thing(self, env, cr, table):
            {cursor}.execute("SELECT * FROM " + table)
        """
        for cursor in ("self.env.cr", "self.cr", "self._cr", "cr", "env.cr"):
            with self.subTest(cursor=cursor):
                self.assertTrue(
                    self._check(snippet.format(cursor=cursor)),
                    f"{cursor} is a cursor; its query has to be checked",
                )

    def test_test_code_is_exempt(self):
        snippet = """
        def do_the_thing(cr, name):
            cr.execute('select %s from thing' % name)
        """
        self.assertTrue(self._check(snippet))
        scope = next(
            checker.applies_to
            for checker in _py_scan.CHECKERS
            if checker.rule == "sql-injection"
        )
        empty = ast.parse("")
        self.assertFalse(
            scope(_py_scan.Unit("a/tests/test_x.py", "", empty, [], True, True))
        )
        self.assertTrue(
            scope(_py_scan.Unit("a/models/x.py", "", empty, [], True, False))
        )


@no_retry
class TestGetTextLint(BaseCase):
    def _check(self, snippet, filepath="not_test.py"):
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        return list(_checker_gettext.check(tree))

    def test_gettext_env(self):
        violations = self._check("""
        def method(self, vars):
            _("something %s %s", *vars)
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertTrue(placeholders, "_() should flag multiple placeholders")

        violations = self._check("""
        def method(self, vars):
            self.env._("something %s %s", *vars)
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertTrue(placeholders, "self.env._() should flag multiple placeholders")

    def test_gettext_variable(self):
        violations = self._check("""
        some_variable = "Roblox Mini Golf! [ACTUALLY FIXED]"
        _(some_variable)
        _lt(513)
        _lt("string but" + "not static")
        _(f"formatted string")
        """)
        variable_violations = [v for v in violations if v.rule == "gettext-variable"]
        self.assertEqual(len(variable_violations), 4)

    def test_placeholder_counting(self):
        def count(text):
            return len(_checker_gettext.PLACEHOLDER_REGEXP.findall(text))

        self.assertEqual(count("%s %s"), 2)
        self.assertEqual(count("Item%s and %s"), 2, "a placeholder may follow a word")
        self.assertEqual(count("%%s %%s"), 0, "escaped percents are not placeholders")
        self.assertEqual(count("%%%s"), 1, "an escaped percent then a real one")
        self.assertEqual(count("100%% of %s and %s"), 2)
        self.assertEqual(count("%(named)s %(other)s"), 0, "named ones are the fix")
        self.assertEqual(count("%i of %i"), 2, "%i is a Python conversion")
        self.assertEqual(count("%u and %u"), 2, "so is %u")
        self.assertEqual(count("%a and %a"), 2, "and %a")

    def test_the_conversion_types_are_the_ones_python_has(self):
        import re as _re

        types = _checker_gettext.PLACEHOLDER_REGEXP.pattern
        for char in "diouxXeEfFgGcrsa":
            with self.subTest(conversion=char):
                self.assertEqual(
                    len(
                        _checker_gettext.PLACEHOLDER_REGEXP.findall(f"%{char} %{char}")
                    ),
                    2,
                )
        for char in "bnwz":
            with self.subTest(conversion=char):
                self.assertFalse(
                    _checker_gettext.PLACEHOLDER_REGEXP.findall(f"%{char}"),
                    f"%{char} raises at runtime; it is not a placeholder",
                )
        self.assertNotIn("bcdeEfFgGnorsxX", _re.sub(r"\s|#.*", "", types))

    def test_gettext_placeholders(self):
        violations = self._check("""
        _("shouldn't match escaped %%s %%s")
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertFalse(placeholders)

        violations = self._check("""
        _("more than one unnamed placeholder: %s %s")
        _lt("with fancy placeholders: %03.14d %-xL")
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertEqual(len(placeholders), 2)

    def test_gettext_repr(self):
        violations = self._check("""
        _("%r shouldn't be part of translated strings")
        _lt("%(with_placeholders_in_between)r")
        """)
        repr_violations = [v for v in violations if v.rule == "gettext-repr"]
        self.assertEqual(len(repr_violations), 2)

    def test_gettext_repr_ignores_escaped_percent(self):
        violations = self._check("""
        _("100%%rare case")
        """)
        repr_violations = [v for v in violations if v.rule == "gettext-repr"]
        self.assertFalse(repr_violations)

    def test_missing_gettext_no_errors(self):
        violations = self._check("""
        raise UserError(_('This is translated'))
        some_var = 'This is not translated'
        raise UserError(some_var)
        raise UserError(some_var + _('This is translated'))
        raise UserError(_('This is translated') and some_var)
        raise UserError(_('This is translated') if true else some_var)
        def some_call():
            return _("nothing")
        some_arr = ["random_string", _("another_random_string")]
        raise UserError(some_arr[0])
        """)
        missing = [v for v in violations if v.rule == "missing-gettext"]
        self.assertEqual(len(missing), 0)

    def test_a_redirect_warning_is_user_facing_too(self):
        violations = list(
            _checker_gettext.check(
                ast.parse('raise RedirectWarning("Configure it", action.id, "Go")')
            )
        )
        self.assertEqual([v.rule for v in violations], ["missing-gettext"])

    def test_missing_gettext_catching_errors(self):
        violations = self._check("""
        UserError('This is not translated')
        exceptions.UserError('This is also not translated')
        UserError(f'This is an f-string')
        raise UserError('This is not translated' + 'This is also not translated')
        some_var = 'random_string'
        raise UserError('This is not translated' and some_var)
        raise UserError('This is not translated' if true else _('This is translated'))
        """)
        missing = [v for v in violations if v.rule == "missing-gettext"]
        self.assertEqual(len(missing), 6)

    def test_a_literal_concatenated_onto_a_translation_still_ships_untranslated(self):
        for snippet, expected in (
            ("""raise UserError(_('Error') + "\\n".join(errors))""", 0),
            ("""raise UserError("Error:\\n" + "\\n".join(errors))""", 1),
            ("""raise UserError(_('Translated') + " and this is not")""", 1),
            ("""raise UserError(prefix + suffix)""", 0),
            ("""raise UserError(_('%(a)s and %(b)s') % {'a': x, 'b': y})""", 0),
        ):
            with self.subTest(snippet=snippet):
                missing = [
                    v for v in self._check(snippet) if v.rule == "missing-gettext"
                ]
                self.assertEqual(len(missing), expected, snippet)


@no_retry
class TestUnlinkLint(BaseCase):
    def _check(self, snippet):
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        return list(_checker_unlink.check(tree))

    def test_raise_in_unlink(self):
        violations = self._check("""
        class MyModel(models.Model):
            def unlink(self):
                if self.state == 'posted':
                    raise UserError("Cannot delete posted record")
                return super().unlink()
        """)
        self.assertTrue(violations, "raise inside unlink should be flagged")

    def test_no_raise_in_unlink(self):
        violations = self._check("""
        class MyModel(models.Model):
            def unlink(self):
                self._check_delete()
                return super().unlink()
        """)
        self.assertFalse(violations, "no raise means no violation")

    def test_non_model_class(self):
        violations = self._check("""
        class NotAModel:
            def unlink(self):
                raise ValueError("this is fine")
        """)
        self.assertFalse(violations, "non-model classes should not be flagged")

    def test_model_variants(self):
        for base in (
            "models.Model",
            "models.TransientModel",
            "models.AbstractModel",
        ):
            with self.subTest(base=base):
                violations = self._check(f"""
                class MyModel({base}):
                    def unlink(self):
                        raise UserError("nope")
                        return super().unlink()
                """)
                self.assertTrue(violations, f"{base} should be detected as model class")


@no_retry
class TestBatchLint(BaseCase):
    def _check(self, snippet, filepath="not_test.py"):
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        return list(_checker_batch.check(tree))

    def test_search_in_for_loop(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                partners = self.env['res.partner'].search([('id', '=', record.id)])
        """)
        self.assertTrue(violations, "search inside for loop should be flagged")
        self.assertIn("search()", violations[0].message)

    def test_search_count_in_for_loop(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                count = self.env['res.partner'].search_count([('id', '=', record.id)])
        """)
        self.assertTrue(violations, "search_count inside for loop should be flagged")
        self.assertIn("search_count()", violations[0].message)

    def test_search_fetch_in_for_loop(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                data = self.env['res.partner'].search_fetch([('id', '=', record.id)], ['name'])
        """)
        self.assertTrue(violations, "search_fetch inside for loop should be flagged")

    def test_read_group_in_for_loop(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                groups = self.env['sale.order']._read_group(
                    [('partner_id', '=', record.id)],
                    groupby=['state'],
                    aggregates=['amount_total:sum'],
                )
        """)
        self.assertTrue(violations, "_read_group inside for loop should be flagged")

    def test_search_outside_loop_ok(self):
        violations = self._check("""
        def process(self, records):
            partners = self.env['res.partner'].search([('active', '=', True)])
            for record in records:
                partner = partners.filtered(lambda p: p.id == record.id)
        """)
        self.assertFalse(violations, "search outside loop should not be flagged")

    def test_nested_for_loop(self):
        violations = self._check("""
        def process(self, orders):
            for order in orders:
                for line in order.order_line:
                    products = self.env['product.product'].search([('id', '=', line.product_id.id)])
        """)
        self.assertTrue(violations, "search in nested loop should be flagged")

    def test_nested_function_def_skipped(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                def helper():
                    return self.env['res.partner'].search([('active', '=', True)])
        """)
        self.assertFalse(
            violations, "search inside nested function should not be flagged"
        )

    def test_lambda_in_loop_not_flagged(self):
        violations = self._check("""
        def process(self, records):
            callbacks = []
            for record in records:
                callbacks.append(lambda: self.env['res.partner'].search([]))
        """)
        self.assertFalse(
            violations, "a lambda defers its body, like the nested def above"
        )

    def test_nested_loops_report_one_query_once(self):
        for depth in (1, 2, 3, 4):
            body = "self.env['res.partner'].search([])"
            for level in range(depth):
                body = f"for x{level} in a:\n    " + body.replace("\n", "\n    ")
            source = "def process(self, a):\n    " + body.replace("\n", "\n    ")
            with self.subTest(depth=depth):
                self.assertEqual(len(self._check(source)), 1)

    def test_async_for_is_a_loop_too(self):
        self.assertTrue(
            self._check("""
        async def process(self, records):
            async for record in records:
                self.env['res.partner'].search([('id', '=', record.id)])
        """),
            "an async for iterates per item, like every other for",
        )

    def test_while_loop_not_flagged(self):
        violations = self._check("""
        def process(self):
            while True:
                results = self.env['res.partner'].search([], limit=100)
                if not results:
                    break
        """)
        self.assertFalse(violations, "while loops should not be flagged")

    def test_for_else_clause_is_not_per_record(self):
        self.assertFalse(
            self._check("""
        def process(self, records):
            for record in records:
                pass
            else:
                self.env['res.partner'].search([])
        """),
            "the else clause runs once, so a query in it is not an N+1",
        )

    def test_a_loop_inside_an_else_clause_is_still_a_loop(self):
        self.assertTrue(
            self._check("""
        def process(self, records, others):
            for record in records:
                pass
            else:
                for other in others:
                    self.env['res.partner'].search([('id', '=', other.id)])
        """),
            "skipping the else clause must not skip a loop nested in it",
        )

    def test_env_on_the_loop_variable_is_an_orm_receiver(self):
        for expression in (
            "record.env['res.partner'].search([])",
            "order.env['lunch.topping'].search_count([])",
            "wizard.env['crm.team'].search([('id', '=', wizard.id)])",
            "request.env['sms.tracker'].search([])",
        ):
            with self.subTest(expression=expression):
                self.assertTrue(
                    self._check(
                        f"def process(self, records):\n"
                        f"    for record in records:\n"
                        f"        {expression}\n"
                    ),
                    "an `.env[...]` subscript is a recordset whatever it hangs off",
                )

    def test_only_search_is_gated_on_its_receiver(self):
        loop = "def process(self, items):\n    for item in items:\n        {}\n"
        self.assertFalse(
            self._check(loop.format("some_regex.search(item)")),
            "a bare name is not an ORM receiver, so `search` is not a query",
        )
        for method in ("search_count", "search_fetch", "_read_group"):
            with self.subTest(method=method):
                self.assertTrue(
                    self._check(loop.format(f"record.{method}([('x', '=', item)])")),
                    f"{method} has no stdlib namesake; a bare recordset name "
                    f"must still count",
                )

    def test_if_inside_loop(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                if record.active:
                    partners = self.env['res.partner'].search([('id', '=', record.id)])
        """)
        self.assertTrue(violations, "search inside if inside loop should be flagged")

    def test_non_query_method_ok(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                record.write({'active': True})
                record.unlink()
                name = record.name_get()
        """)
        self.assertFalse(violations, "non-query methods should not be flagged")

    def test_regex_search_not_flagged(self):
        violations = self._check("""
        import re
        PATTERN = re.compile(r'\\w+')
        def process(self, nodes):
            for node in nodes:
                if re.search(r'pattern', node.text):
                    pass
                if PATTERN.search(node.text):
                    pass
                if some_regex.search(node.text):
                    pass
        """)
        self.assertFalse(violations, "regex search should not be flagged")

    def test_a_compiled_regex_is_not_an_orm_query(self):
        self.assertFalse(
            self._check("""
        import re
        def process(self, nodes):
            for node in nodes:
                if re.compile(r'pattern').search(node.text):
                    pass
        """),
            "a compiled regex is not a recordset",
        )

    def test_a_recordset_returning_call_is_still_an_orm_receiver(self):
        for expression in (
            "IrAttachment.sudo().search([])",
            "request.env['sms.tracker'].sudo().search([])",
            "lead.with_context(active_test=False).search([])",
            "comodel.with_context(active_test=False).search([])",
            "model.sudo().search_count([])",
        ):
            with self.subTest(expression=expression):
                self.assertTrue(
                    self._check(
                        f"def process(self, records):\n"
                        f"    for record in records:\n"
                        f"        {expression}\n"
                    ),
                    "a recordset-returning method makes this an ORM query",
                )

    def test_orm_search_on_self_flagged(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                self.search([('id', '=', record.id)])
                self.env['res.partner'].search([('id', '=', record.id)])
                self.sudo().search([('id', '=', record.id)])
        """)
        self.assertEqual(
            len(violations), 3, "all three ORM search calls should be flagged"
        )

    def test_model_class_search_flagged(self):
        violations = self._check("""
        def process(self, records):
            for record in records:
                Partner.search([('id', '=', record.id)])
        """)
        self.assertTrue(violations, "CamelCase model search should be flagged")


@no_retry
class TestSuppressionSpans(BaseCase):
    @staticmethod
    def _spans(source: str) -> dict[int, int]:
        return _rules.statement_spans(_rules.walk_with_parents(ast.parse(source)))

    def _suppresses(self, source: str, lineno: int, rule: str) -> bool:
        lines = _rules.directive_lines(self._spans(source), lineno)
        return _suppression.Suppressions.of(
            source, _rules.ALIASES, _rules.UNSUPPRESSABLE
        ).suppresses(lineno, rule, lines)

    def test_a_directive_opening_a_wrapped_call_reaches_a_finding_inside_it(self):
        source = dedent("""\
            def f(self, op, column):
                return SQL(  # pylint: disable=sql-injection
                    "%s(%s)", SQL(op.value), column
                )
            """)
        self.assertTrue(self._suppresses(source, 3, "sql-injection"))

    def test_a_directive_on_the_closing_line_of_a_wrapped_call_counts(self):
        source = dedent("""\
            def f(self, t):
                self.env.cr.execute(
                    f"SELECT {t}"
                )  # noqa: E8501  the table name comes from _table
            """)
        self.assertTrue(self._suppresses(source, 2, "sql-injection"))

    def test_a_directive_on_the_line_itself_still_counts(self):
        source = "x = 1  # noqa: E8501  because\n"
        self.assertTrue(self._suppresses(source, 1, "sql-injection"))

    def test_a_directive_past_the_statement_does_not_count(self):
        source = dedent("""\
            def f(self, t):
                self.env.cr.execute(
                    f"SELECT {t}"
                )
                other()  # noqa: E8501  a different statement
            """)
        self.assertFalse(self._suppresses(source, 2, "sql-injection"))

    def test_a_block_body_cannot_waive_its_own_header(self):
        source = dedent("""\
            def build(table):
                x = 1  # noqa: E8501  unrelated
                return f"SELECT {table}"
            """)
        self.assertEqual(self._spans(source).get(1, 1), 1)
        self.assertFalse(self._suppresses(source, 1, "sql-injection"))


@no_retry
class TestTaxCompanySingularLint(BaseCase):
    def _check(self, snippet):
        return [
            v.lineno
            for v in _checker_tax_company.check(ast.parse(dedent(snippet).strip()))
        ]

    def test_filtered_over_a_tax_field_is_flagged(self):
        self.assertEqual(
            self._check("""
        taxes = product.taxes_id.filtered(lambda t: t.company_id == company)
        """),
            [1],
        )

    def test_a_compound_lambda_is_flagged(self):
        self.assertEqual(
            self._check("""
        taxes = product.supplier_taxes_id.filtered(
            lambda t: t.active and t.company_id in company.parent_ids
        )
        """),
            [2],
        )

    def test_the_many2many_spelling_is_clean(self):
        self.assertFalse(
            self._check("""
        taxes = line.tax_ids.filtered(lambda t: company in t.company_ids)
        """)
        )

    def test_filtered_domain_is_clean(self):
        self.assertFalse(
            self._check("""
        taxes = product.taxes_id.filtered_domain(domain)
        """)
        )

    def test_company_id_on_a_non_tax_field_is_clean(self):
        self.assertFalse(
            self._check("""
        lines = order.line_ids.filtered(lambda l: l.company_id == company)
        """)
        )

    def test_a_shadowing_outer_name_is_not_the_lambda_parameter(self):
        self.assertFalse(
            self._check("""
        taxes = product.taxes_id.filtered(lambda t: other.company_id == company)
        """)
        )

    def test_the_message_names_the_replacement(self):
        [violation] = _checker_tax_company.check(
            ast.parse("x = p.taxes_id.filtered(lambda t: t.company_id == c)")
        )
        self.assertIn("company_ids", violation.message)
        self.assertIn("_check_company_domain", violation.message)

    def test_a_company_id_domain_on_a_diverged_model_is_flagged(self):
        self.assertEqual(
            self._check("""
        groups = self.env["account.tax"].sudo()._read_group(
            domain=[("company_id", "in", self.company_ids.ids)],
            aggregates=["tax_group_id:recordset"],
        )
        """),
            [2],
        )

    def test_a_model_bound_from_a_tuple_of_names_is_flagged(self):
        self.assertEqual(
            self._check("""
        for model in ("account.tax", "account.tax.group"):
            cls.env[model].search([("company_id", "=", company.id)])
        """),
            [2],
        )

    def test_account_account_is_diverged_too(self):
        self.assertEqual(
            self._check("""
        accounts = self.env["account.account"].search([("company_id", "=", c.id)])
        """),
            [1],
        )

    def test_the_check_company_domain_idiom_is_clean(self):
        self.assertFalse(
            self._check("""
        taxes = self.env["account.tax"].search(
            self.env["account.tax"]._check_company_domain(company)
        )
        """)
        )

    def test_a_company_id_domain_on_another_model_is_clean(self):
        self.assertFalse(
            self._check("""
        lines = self.env["account.move.line"].search([("company_id", "=", c.id)])
        """)
        )

    def test_the_many2many_domain_spelling_is_clean(self):
        self.assertFalse(
            self._check("""
        taxes = self.env["account.tax"].search([("company_ids", "in", c.ids)])
        """)
        )

    def test_a_model_chosen_at_runtime_is_not_decided(self):
        self.assertFalse(
            self._check("""
        records = self.env[template.model].search([("company_id", "in", ids)])
        """)
        )


@no_retry
class TestShadowedDefinitionLint(BaseCase):
    def _check(self, snippet):
        return [
            v.message
            for v in _checker_shadowed_def.check(ast.parse(dedent(snippet).strip()))
        ]

    def test_a_plain_second_definition_is_flagged(self):
        self.assertTrue(
            self._check("""
        class A:
            def f(self):
                pass

            def f(self):
                pass
        """)
        )

    def test_the_message_names_the_definition_that_died(self):
        [message] = self._check("""
        class A:
            def f(self):
                pass

            def f(self):
                pass
        """)
        self.assertIn("A.f", message)
        self.assertIn("line 2", message)

    def test_a_decorator_does_not_make_it_legitimate(self):
        self.assertTrue(
            self._check("""
        class A:
            @api.model
            def f(self):
                pass

            @api.model
            def f(self):
                pass
        """),
            "two @api.model methods of the same name still shadow one another",
        )

    def test_an_overload_stack_is_not_a_finding(self):
        self.assertFalse(
            self._check("""
        class A:
            @typing.overload
            def f(self, x: int) -> int: ...

            @typing.overload
            def f(self, x: str) -> str: ...

            def f(self, x):
                return x
        """)
        )

    def test_a_setter_of_another_property_is_still_a_redefinition(self):
        violations = self._check("""
        class C:
            @property
            def f(self):
                return 1

            @g.setter
            def f(self, value):
                pass
        """)
        self.assertEqual(len(violations), 1)
        self.assertIn("C.f", violations[0])

    def test_a_property_group_is_not_a_finding(self):
        self.assertFalse(
            self._check("""
        class A:
            @property
            def f(self):
                pass

            @f.setter
            def f(self, value):
                pass

            @f.deleter
            def f(self):
                pass
        """)
        )

    def test_a_single_dispatch_group_is_not_a_finding(self):
        self.assertFalse(
            self._check("""
        class A:
            @singledispatchmethod
            def f(self, value):
                pass

            @f.register
            def _(self, value: int):
                pass
        """)
        )

    def test_an_unrelated_register_decorator_is_still_flagged(self):
        self.assertTrue(
            self._check("""
        class A:
            def f(self):
                pass

            @some_registry.register
            def f(self):
                pass
        """),
            "a `.register` decorator unrelated to singledispatchmethod must not"
            " exempt a genuine shadowed definition",
        )

    def test_definitions_in_different_branches_are_alternatives(self):
        self.assertFalse(
            self._check("""
        class A:
            if typing.TYPE_CHECKING:
                def f(self) -> int: ...
            else:
                def f(self):
                    return 1
        """),
            "only one of the two ever reaches the class body",
        )

    def test_a_nested_class_has_its_own_namespace(self):
        self.assertFalse(
            self._check("""
        class A:
            def f(self):
                pass

            class B:
                def f(self):
                    pass
        """)
        )

    def test_async_definitions_count_too(self):
        self.assertTrue(
            self._check("""
        class A:
            async def f(self):
                pass

            async def f(self):
                pass
        """)
        )


@no_retry
class TestHttpJsonLint(BaseCase):
    def _check(self, snippet):
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        return list(_checker_http_json.check(tree))

    def test_bare_json_dumps_in_an_http_route(self):
        violations = self._check("""
        class C(http.Controller):
            @http.route("/x", type="http", auth="public")
            def x(self):
                if not self.ok():
                    return json.dumps({"error": "forbidden"})
                return json.dumps({"id": 1})
        """)
        self.assertEqual([v.lineno for v in violations], [5, 6])

    def test_type_defaults_to_http(self):
        violations = self._check("""
        class C(http.Controller):
            @route("/x", auth="public")
            def x(self):
                return json.dumps([])
        """)
        self.assertTrue(violations)

    def test_jsonrpc_routes_and_typed_answers_pass(self):
        violations = self._check("""
        class C(http.Controller):
            @http.route("/x", type="jsonrpc", auth="public")
            def x(self):
                return json.dumps({"id": 1})

            @http.route("/y", type="http", auth="public")
            def y(self):
                return request.prepare_json_response({"id": 1})

            @http.route("/z", type="http", auth="public")
            def z(self):
                def inner():
                    return json.dumps({})
                return inner()
        """)
        self.assertFalse(violations)


@no_retry
class TestRawEgressLint(BaseCase):
    def _targets(self, snippet):
        tree = ast.parse(dedent(snippet).strip())
        return [
            v.message.split("()")[0] for v in _checker_egress.check_raw_egress(tree)
        ]

    def test_requests_calls_and_sessions_are_egress(self):
        self.assertEqual(
            self._targets("""
            import requests
            requests.post(url, json={})
            session = requests.Session()
            """),
            ["requests.post", "requests.Session"],
        )

    def test_the_lowercase_session_factory_is_egress(self):
        self.assertEqual(
            self._targets("""
            import requests
            from requests.sessions import session
            requests.session()
            session()
            """),
            ["requests.session", "requests.sessions.session"],
        )

    def test_aliases_and_from_imports_are_followed(self):
        self.assertEqual(
            self._targets("""
            import requests as r
            from requests import get
            from urllib.request import urlopen
            import boto3
            from zeep import Transport
            r.get(url)
            get(url)
            urlopen(url)
            boto3.client("s3")
            Transport(timeout=5)
            """),
            [
                "requests.get",
                "requests.get",
                "urllib.request.urlopen",
                "boto3.client",
                "zeep.Transport",
            ],
        )

    def test_a_session_method_on_a_local_name_is_not_guessed_at(self):
        self.assertEqual(
            self._targets("""
            client = get_api_client(env, "x")
            client.post("/y")
            requests_count = 3
            """),
            [],
        )

    def test_the_transport_module_has_no_exemption(self):
        unit = _rules.Unit(
            "/w/odoo/addons/integration/tools/api_client.py",
            "",
            ast.parse(""),
            [],
            True,
        )
        applies = next(c for c in _rules.CHECKERS if "raw-egress" in c.rules).applies_to
        self.assertTrue(applies(unit))


@no_retry
class TestSecretInEnvironLint(BaseCase):
    def _count(self, snippet):
        tree = ast.parse(dedent(snippet).strip())
        return len(list(_checker_egress.check_secret_in_environ(tree)))

    def test_a_secret_written_into_the_worker_environment_is_flagged(self):
        self.assertEqual(
            self._count("""
            import os
            os.environ["ANTHROPIC_API_KEY"] = key
            os.environ.setdefault("GH_TOKEN", token)
            os.environ.update({"DB_PASSWORD": pw})
            os.putenv("AWS_SECRET_ACCESS_KEY", secret)
            """),
            4,
        )

    def test_non_secret_variables_and_child_env_mappings_are_fine(self):
        self.assertEqual(
            self._count("""
            import os
            os.environ["TZ"] = "UTC"
            env = {**os.environ, "ANTHROPIC_API_KEY": key}
            subprocess.run(cmd, env=env)
            """),
            0,
        )


@no_retry
class TestCredentialStorageLint(BaseCase):
    def _fields(self, snippet, path="/w/odoo/addons/payment_x/models/provider.py"):
        tree = ast.parse(dedent(snippet).strip())
        return [
            v.message.split(" ")[0]
            for v in _checker_credential_storage.check(tree, path)
        ]

    def test_a_stored_secret_column_is_flagged(self):
        self.assertEqual(
            self._fields("""
            class Provider(models.Model):
                x_secret_key = fields.Char(groups="base.group_system")
                x_webhook_token = fields.Text()
            """),
            ["payment_x.x_secret_key", "payment_x.x_webhook_token"],
        )

    def test_computed_share_public_derived_and_hashed_fields_are_not_secrets(self):
        self.assertEqual(
            self._fields("""
            class Provider(models.Model):
                x_api_key = fields.Char(compute="_compute_x_api_key")
                share_token = fields.Char()
                x_publishable_key = fields.Char()
                x_token_hash = fields.Char()
                x_password = fields.Char()

                def _set(self, value):
                    self.x_password = crypt_context.hash(value)
            """),
            [],
        )

    def test_the_names_of_a_scheme_an_endpoint_and_a_booking_path_are_not_secrets(self):
        self.assertEqual(
            self._fields("""
            class Service(models.Model):
                api_key_scheme = fields.Char()
                oauth_token_endpoint = fields.Char()
                booking_key = fields.Char()
            """),
            [],
        )

    def test_a_settings_secret_kept_in_config_parameters_is_flagged(self):
        self.assertEqual(
            self._fields("""
            class Settings(models.TransientModel):
                x_client_secret = fields.Char(config_parameter="x.client_secret")
                x_wizard_password = fields.Char()
            """),
            ["payment_x.x_client_secret"],
        )

    def test_a_secret_parameter_read_or_written_by_key_is_flagged(self):
        self.assertEqual(
            self._fields("""
            class Settings(models.TransientModel):
                def _inverse_x_client_secret(self):
                    ICP = self.env["ir.config_parameter"].sudo()
                    ICP.set_param("x.client_secret", self.x_client_secret)

                def _read(self):
                    ICP = self.env["ir.config_parameter"].sudo()
                    return ICP.get_param("x.private_key"), ICP.get_param("x.client_id")
            """),
            ["x.client_secret", "x.private_key"],
        )

    def test_a_judged_or_public_parameter_is_not_a_secret(self):
        self.assertEqual(
            self._fields("""
            def _read(env):
                ICP = env["ir.config_parameter"].sudo()
                ICP.get_param("database.secret")
                ICP.get_param("mail.web_push_vapid_public_key")
                ICP.get_param("x.token_endpoint")
            """),
            [],
        )

    def test_the_vault_itself_is_out_of_scope(self):
        self.assertEqual(
            self._fields(
                """
                class Credential(models.Model):
                    api_secret = fields.Char()
                """,
                path="/w/odoo/addons/credential/models/credential_credential.py",
            ),
            [],
        )


@no_retry
class TestFieldDeclarationLint(BaseCase):
    def _check(self, source, rule=None):
        tree = ast.parse(dedent(source))
        return [
            (v.rule, v.lineno)
            for v in _checker_field_declaration.check(
                tree, _rules.walk_with_parents(tree)
            )
            if rule is None or v.rule == rule
        ]

    def test_a_field_declared_twice_is_flagged_at_the_second(self):
        found = self._check("""
        class Partner(models.Model):
            show_credit_limit = fields.Boolean(groups="a")
            use_credit_limit = fields.Boolean()

            show_credit_limit = fields.Boolean(groups="b")
        """)
        self.assertEqual(found, [("field-redeclared", 6)])

    def test_a_field_overwriting_a_plain_attribute_is_flagged_too(self):
        found = self._check("""
        class Partner(models.Model):
            _order = "name"
            _order = fields.Char()
        """)
        self.assertEqual(found, [("field-redeclared", 4)])

    def test_two_plain_attributes_and_two_classes_are_not_a_redeclaration(self):
        self.assertEqual(
            self._check("""
        class A(models.Model):
            _order = "name"
            _order = "id"
            name = fields.Char()

        class B(models.Model):
            name = fields.Char()
        """),
            [],
        )

    def test_a_default_that_ran_at_import_is_flagged(self):
        for default in (
            "fields.Date.today()",
            "fields.Datetime.now()",
            "datetime.now()",
            "uuid.uuid4()",
            "secrets.token_hex(16)",
            '_("New")',
        ):
            with self.subTest(default=default):
                found = self._check(f"""
                class Wizard(models.TransientModel):
                    date = fields.Date(default={default})
                """)
                self.assertEqual(found, [("default-evaluated-at-import", 3)])

    def test_a_callable_or_constant_default_is_fine(self):
        self.assertEqual(
            self._check("""
        class Wizard(models.TransientModel):
            date = fields.Date(default=fields.Date.today)
            when = fields.Datetime(default=lambda self: fields.Datetime.now())
            code = fields.Char(default=",".join(CODES))
            since = fields.Datetime(default=datetime(2018, 1, 1))
            label = fields.Char(default=_lt("New"))
        """),
            [],
        )

    def test_a_repeated_selection_key_is_flagged(self):
        found = self._check(
            """
        class Move(models.Model):
            kind = fields.Selection(
                [("23", "Credit note"), ("30", "Debit note"), ("23", "Inactive")],
            )
            other = fields.Selection(selection=[("a", "A"), ("a", "B")])
            clean = fields.Selection([("a", "A"), ("b", "B")])
            dynamic = fields.Selection(selection="_selection_dynamic")
        """,
            rule="selection-duplicate-key",
        )
        self.assertEqual(
            found,
            [("selection-duplicate-key", 4), ("selection-duplicate-key", 6)],
        )

    def test_a_hook_outside_its_family_is_flagged(self):
        found = self._check(
            """
        class Users(models.Model):
            totp_enabled = fields.Boolean(compute="_compute_totp_enabled", search="_totp_enable_search")
            cert = fields.Binary(compute="_compute_cert", inverse="_set_cert")
            kind = fields.Selection(selection="_get_kinds")
            fine = fields.Char(compute="_compute_fine", inverse="_inverse_fine", search="_search_fine")
            shared = fields.Float(compute="_compute_amounts")
        """,
            rule="field-hook-prefix",
        )
        self.assertEqual(
            found,
            [
                ("field-hook-prefix", 3),
                ("field-hook-prefix", 4),
                ("field-hook-prefix", 5),
            ],
        )

    def test_a_positional_argument_is_named_after_its_parameter(self):
        found = [
            (v.rule, v.message)
            for v in _checker_field_declaration.check(
                ast.parse(
                    dedent("""
                    class M(models.Model):
                        line_ids = fields.One2many("m.line", "m_id", "Lines")
                        tag_ids = fields.Many2many("m.tag", "rel", "a", "b")
                    """)
                )
            )
            if v.rule == "field-positional-argument"
        ]
        self.assertEqual(len(found), 2)
        self.assertIn("comodel_name=, inverse_name=, string=", found[0][1])
        self.assertIn("comodel_name=, relation=, column1=, column2=", found[1][1])

    def test_keywords_out_of_order_or_sharing_a_line_are_flagged(self):
        found = self._check(
            """
        class M(models.Model):
            a = fields.Char(required=True, string="A")
            b = fields.Char(string="B", required=True)
            c = fields.Char(
                string="C",
                required=True,
            )
            d = fields.Char(string="D")
            e = fields.Char(string="E",
                            required=True)
        """,
            rule="field-attribute-order",
        )
        self.assertEqual(
            found,
            [
                ("field-attribute-order", 3),
                ("field-attribute-order", 4),
                ("field-attribute-order", 10),
            ],
        )

    def test_the_canonical_order_reads_what_it_is_before_how_it_is_stored(self):
        self.assertEqual(
            _checker_field_declaration.canonical_order(
                [
                    "help",
                    "store",
                    "groups",
                    "string",
                    "compute",
                    "comodel_name",
                    "zzz_custom",
                ]
            ),
            [
                "comodel_name",
                "string",
                "compute",
                "store",
                "zzz_custom",
                "groups",
                "help",
            ],
        )

    def test_an_attribute_setup_ignores_is_flagged(self):
        found = self._check(
            """
        class M(models.Model):
            tag_ids = fields.Many2many(
                comodel_name="m.tag",
                index=True,
            )
            total = fields.Float(
                compute="_compute_total",
                index=True,
            )
            kind = fields.Selection(
                selection=[("a", "A")],
                compute="_compute_kind",
                precompute=True,
            )
            partner_name = fields.Char(
                related="partner_id.name",
                compute="_compute_partner_name",
            )
            stored = fields.Float(
                compute="_compute_stored",
                precompute=True,
                store=True,
                index=True,
            )
            unrelated = fields.Char(
                related=False,
                compute="_compute_unrelated",
            )
            extended = fields.Selection(
                required=True,
                precompute=True,
            )
        """,
            rule="dead-field-attribute",
        )
        self.assertEqual(
            found,
            [
                ("dead-field-attribute", 3),
                ("dead-field-attribute", 7),
                ("dead-field-attribute", 11),
                ("dead-field-attribute", 16),
            ],
        )

    def test_a_stored_copy_of_a_related_value_is_flagged(self):
        found = self._check(
            """
        class M(models.Model):
            company_id = fields.Many2one(
                related="order_id.company_id",
                store=True,
            )
            currency_id = fields.Many2one(
                related="order_id.currency_id",
            )
            image_128 = fields.Image(
                related="image_1920",
                max_width=128,
                store=True,
            )
            state = fields.Selection(
                related="order_id.state",
                store=False,
            )
        """,
            rule="stored-related",
        )
        self.assertEqual(found, [("stored-related", 3)])

    def test_the_label_position_of_each_relational_class_is_known(self):
        call = (
            ast.parse('fields.Many2many("a", "rel", "c1", "c2", "Label")').body[0].value
        )
        self.assertEqual(
            _checker_field_declaration.string_argument(call).value, "Label"
        )
        call = ast.parse('fields.One2many("a", "b_id", "Lines")').body[0].value
        self.assertEqual(
            _checker_field_declaration.string_argument(call).value, "Lines"
        )
        call = ast.parse('fields.Many2one("a", "Partner")').body[0].value
        self.assertEqual(
            _checker_field_declaration.string_argument(call).value, "Partner"
        )
        call = ast.parse('fields.Selection([("a", "A")], "Kind")').body[0].value
        self.assertEqual(_checker_field_declaration.string_argument(call).value, "Kind")
        call = ast.parse('fields.Char("Name")').body[0].value
        self.assertEqual(_checker_field_declaration.string_argument(call).value, "Name")
        call = ast.parse('fields.Many2one("a")').body[0].value
        self.assertIsNone(_checker_field_declaration.string_argument(call))


class TestReceiverFailOpenLint(BaseCase):
    def _routes(self, snippet):
        tree = ast.parse(dedent(snippet).strip())
        return [v.message.split(":")[0] for v in _checker_receiver.check(tree)]

    def test_an_open_route_that_reaches_no_gate_is_flagged(self):
        self.assertEqual(
            self._routes("""
            class Hooks(http.Controller):
                @http.route("/hook", type="http", auth="public", csrf=False)
                def hook(self, **kw):
                    return self._handle(request.get_json_data())

                def _handle(self, data):
                    return data
            """),
            ["hook"],
        )

    def test_a_route_that_resolves_its_caller_through_a_helper_is_not(self):
        self.assertEqual(
            self._routes("""
            class Hooks(http.Controller):
                @route("/hook/<id>", type="http", auth="none", csrf=False)
                def hook(self, id, **kw):
                    device = self._resolve(id)
                    return device

                def _resolve(self, id):
                    device = request.env["x"].search([("id", "=", id)])
                    device.check_inbound_auth(dict(request.httprequest.headers), "1")
                    return device
            """),
            [],
        )

    def test_a_route_with_a_session_or_csrf_is_out_of_scope(self):
        self.assertEqual(
            self._routes("""
            class Pages(http.Controller):
                @http.route("/page", type="http", auth="user", csrf=False)
                def page(self):
                    return ""

                @http.route("/form", type="http", auth="public")
                def form(self):
                    return ""
            """),
            [],
        )
