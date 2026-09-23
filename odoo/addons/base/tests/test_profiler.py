import sys
import time
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.libs.profiling import Speedscope
from odoo.tests.common import (
    BaseCase,
    HttpCase,
    TransactionCase,
    new_test_user,
    tagged,
)
from odoo.tools import profiler
from odoo.tools.profiler import ExecutionContext, Profiler


@tagged("post_install", "-at_install", "profiling")
class TestProfileAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_profile = cls.env["ir.profile"].create({})

    def test_admin_has_access(self):
        self.assertEqual(
            self.env["ir.profile"].search([("id", "=", self.test_profile.id)]),
            self.test_profile,
        )
        self.test_profile.read(["name"])

    def test_user_no_access(self):
        user = new_test_user(self.env, login="noProfile", groups="base.group_user")
        with self.with_user("noProfile"), self.assertRaises(AccessError):
            self.env["ir.profile"].search([])
        with self.assertRaises(AccessError):
            self.test_profile.with_user(user).read(["name"])

    def test_action_view_speedscope_url(self):
        action = self.test_profile.action_view_speedscope()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertTrue(action["url"].startswith("/web/profile_config/"))

    def test_generate_speedscope_check_access(self):
        user = new_test_user(self.env, login="noProfileSpeed", groups="base.group_user")
        params = self.test_profile._parse_params({})
        with self.assertRaises(AccessError):
            self.test_profile.with_user(user)._generate_speedscope(params)

    def test_generate_memory_profile_check_access(self):
        user = new_test_user(self.env, login="noProfileMem", groups="base.group_user")
        params = self.test_profile._parse_params({})
        with self.assertRaises(AccessError):
            self.test_profile.with_user(user)._generate_memory_profile(params)

    def test_speedscope_url_no_speedscope_dependency(self):
        IrProfile = type(self.env["ir.profile"])
        with patch.object(
            IrProfile, "_compute_speedscope", autospec=True
        ) as compute_speedscope:
            self.assertEqual(
                self.test_profile.speedscope_url,
                f"/web/speedscope/{self.test_profile.id}",
            )
        compute_speedscope.assert_not_called()


@tagged("post_install", "-at_install", "profiling")
class TestSpeedscope(BaseCase):
    def example_profile(self):
        return {
            "init_stack_trace": [["/path/to/file_1.py", 135, "__main__", "main()"]],
            "result": [
                {
                    "start": 2.0,
                    "exec_context": (),
                    "stack": [
                        [
                            "/path/to/file_1.py",
                            10,
                            "main",
                            "do_stuff1(test=do_tests)",
                        ],
                        [
                            "/path/to/file_1.py",
                            101,
                            "do_stuff1",
                            "cr.execute(query, params)",
                        ],
                    ],
                },
                {
                    "start": 3.0,
                    "exec_context": (),
                    "stack": [
                        [
                            "/path/to/file_1.py",
                            10,
                            "main",
                            "do_stuff1(test=do_tests)",
                        ],
                        [
                            "/path/to/file_1.py",
                            101,
                            "do_stuff1",
                            "cr.execute(query, params)",
                        ],
                        [
                            "/path/to/cursor.py",
                            650,
                            "execute",
                            "res = self._obj.execute(query, params)",
                        ],
                    ],
                },
                {
                    "start": 4.0,
                    "exec_context": (),
                    "stack": [
                        [
                            "/path/to/file_1.py",
                            10,
                            "main",
                            "do_stuff1(test=do_tests)",
                        ],
                        [
                            "/path/to/file_1.py",
                            101,
                            "do_stuff1",
                            "cr.execute(query, params)",
                        ],
                        [
                            "/path/to/cursor.py",
                            650,
                            "execute",
                            "res = self._obj.execute(query, params)",
                        ],
                    ],
                },
                {
                    "start": 6.0,
                    "exec_context": (),
                    "stack": [
                        [
                            "/path/to/file_1.py",
                            10,
                            "main",
                            "do_stuff1(test=do_tests)",
                        ],
                        ["/path/to/file_1.py", 101, "do_stuff1", "check"],
                        ["/path/to/cursor.py", 650, "check", "assert x = y"],
                    ],
                },
                {
                    "start": 10.0,
                    "exec_context": (),
                    "stack": [
                        [
                            "/path/to/file_1.py",
                            10,
                            "main",
                            "do_stuff1(test=do_tests)",
                        ],
                        [
                            "/path/to/file_1.py",
                            101,
                            "do_stuff1",
                            "for i in range(10):",
                        ],
                    ],
                },
                {
                    "start": 10.35,
                    "exec_context": (),
                    "stack": None,
                },
            ],
        }

    def test_convert_empty(self):
        Speedscope().prepare_document()

    def test_converts_profile_simple(self):
        profile = self.example_profile()

        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=False)
        res = sp.prepare_document()

        frames = res["shared"]["frames"]
        self.assertEqual(len(frames), 4)

        profile_combined = res["profiles"][0]
        events = [(e["type"], e["frame"]) for e in profile_combined["events"]]
        self.assertEqual(
            events,
            [
                ("O", 0),
                ("O", 1),
                ("O", 2),
                ("C", 2),
                ("O", 3),
                ("C", 3),
                ("C", 1),
                ("C", 0),
            ],
        )
        self.assertEqual(profile_combined["events"][0]["at"], 0.0)
        self.assertEqual(profile_combined["events"][-1]["at"], 8.35)

    def test_converts_profile_no_end(self):
        profile = self.example_profile()
        profile["result"].pop()
        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=False)
        res = sp.prepare_document()
        profile_combined = res["profiles"][0]
        events = [(e["type"], e["frame"]) for e in profile_combined["events"]]

        self.assertEqual(
            events,
            [
                ("O", 0),
                ("O", 1),
                ("O", 2),
                ("C", 2),
                ("O", 3),
                ("C", 3),
                ("C", 1),
                ("C", 0),
            ],
        )
        self.assertEqual(profile_combined["events"][-1]["at"], 8)

    def test_converts_init_stack_trace(self):
        profile = self.example_profile()

        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=True)
        res = sp.prepare_document()

        profile_combined = res["profiles"][0]
        events = [(e["type"], e["frame"]) for e in profile_combined["events"]]

        self.assertEqual(
            events,
            [
                ("O", 4),
                ("O", 0),
                ("O", 1),
                ("O", 2),
                ("C", 2),
                ("O", 3),
                ("C", 3),
                ("C", 1),
                ("C", 0),
                ("C", 4),
            ],
        )
        self.assertEqual(profile_combined["events"][-1]["at"], 8.35)

    def test_end_priority(self):

        async_profile = self.example_profile()["result"]
        sql_profile = self.example_profile()["result"]
        sql_profile = [sql_profile[1]]
        sql_profile[0]["start"] = 2.5
        sql_profile[0]["time"] = 3
        sql_profile[0]["query"] = "SELECT 1"
        sql_profile[0]["full_query"] = "SELECT 1"
        self.assertEqual(async_profile[1]["start"], 3)
        self.assertEqual(async_profile[2]["start"], 4)

        self.assertNotIn("query", async_profile[1]["stack"])
        self.assertNotIn("time", async_profile[1]["stack"])
        self.assertEqual(async_profile[1]["stack"], async_profile[2]["stack"])

        sp = Speedscope(init_stack_trace=[])
        sp.add("sql", async_profile)
        sp.add("traces", sql_profile)
        sp.add_output(["sql", "traces"], complete=False)
        res = sp.prepare_document()
        profile_combined = res["profiles"][0]
        events = [
            (
                e["at"] + 2,
                e["type"],
                res["shared"]["frames"][e["frame"]]["name"],
            )
            for e in profile_combined["events"]
        ]
        self.assertEqual(
            events,
            [
                (2.0, "O", "main"),
                (2.0, "O", "do_stuff1"),
                (2.5, "O", "execute"),
                (2.5, "O", "sql('SELECT 1')"),
                (
                    5.5,
                    "C",
                    "sql('SELECT 1')",
                ),
                (5.5, "C", "execute"),
                (6.0, "O", "check"),
                (10.0, "C", "check"),
                (10.35, "C", "do_stuff1"),
                (10.35, "C", "main"),
            ],
        )

    def test_following_queries_dont_merge(self):
        sql_profile = self.example_profile()["result"]
        stack = sql_profile[1]["stack"]
        sql_profile = [
            {
                "start": 0.0,
                "time": 1,
                "query": "SELECT 1",
                "full_query": "SELECT 1",
                "stack": stack[:],
            },
            {
                "start": 10.0,
                "time": 1,
                "query": "SELECT 1",
                "full_query": "SELECT 1",
                "stack": stack[:],
            },
        ]
        sp = Speedscope(init_stack_trace=[])
        sp.add("sql", sql_profile)
        sp.add_output(["sql"], complete=False, hide_gaps=True)
        res = sp.prepare_document()
        sql_output = res["profiles"][0]
        events = [
            (e["at"], e["type"], res["shared"]["frames"][e["frame"]]["name"])
            for e in sql_output["events"]
        ]
        self.assertEqual(
            events,
            [
                (0.0, "O", "main"),
                (0.0, "O", "do_stuff1"),
                (0.0, "O", "execute"),
                (0.0, "O", "sql('SELECT 1')"),
                (2.0, "C", "sql('SELECT 1')"),
                (2.0, "C", "execute"),
                (2.0, "C", "do_stuff1"),
                (2.0, "C", "main"),
            ],
        )

    def test_converts_context(self):
        stack = [
            ["file.py", 10, "level1", "level1"],
            ["file.py", 11, "level2", "level2"],
        ]
        profile = {
            "init_stack_trace": [["file.py", 1, "level0", "level0)"]],
            "result": [
                {
                    "start": 2.0,
                    "exec_context": ((2, {"a": "1"}), (3, {"b": "1"})),
                    "stack": list(stack),
                },
                {
                    "start": 3.0,
                    "exec_context": ((2, {"a": "1"}), (3, {"b": "2"})),
                    "stack": list(stack),
                },
                {
                    "start": 10.35,
                    "exec_context": (),
                    "stack": None,
                },
            ],
        }
        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=True)
        res = sp.prepare_document()
        events = [
            (e["type"], res["shared"]["frames"][e["frame"]]["name"])
            for e in res["profiles"][0]["events"]
        ]
        self.assertEqual(
            events,
            [
                ("O", "level0"),
                ("O", "a=1"),
                ("O", "level1"),
                ("O", "b=1"),
                ("O", "level2"),
                ("C", "level2"),
                ("C", "b=1"),
                ("O", "b=2"),
                ("O", "level2"),
                ("C", "level2"),
                ("C", "b=2"),
                ("C", "level1"),
                ("C", "a=1"),
                ("C", "level0"),
            ],
        )

    def test_converts_context_nested(self):
        stack = [
            ["file.py", 10, "level1", "level1"],
            ["file.py", 11, "level2", "level2"],
        ]
        profile = {
            "init_stack_trace": [["file.py", 1, "level0", "level0)"]],
            "result": [
                {
                    "start": 2.0,
                    "exec_context": (
                        (3, {"a": "1"}),
                        (3, {"b": "1"}),
                    ),
                    "stack": list(stack),
                },
                {
                    "start": 10.35,
                    "exec_context": (),
                    "stack": None,
                },
            ],
        }
        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=True)
        res = sp.prepare_document()
        events = [
            (e["type"], res["shared"]["frames"][e["frame"]]["name"])
            for e in res["profiles"][0]["events"]
        ]
        self.assertEqual(
            events,
            [
                ("O", "level0"),
                ("O", "level1"),
                ("O", "a=1"),
                ("O", "b=1"),
                ("O", "level2"),
                ("C", "level2"),
                ("C", "b=1"),
                ("C", "a=1"),
                ("C", "level1"),
                ("C", "level0"),
            ],
        )

    def test_converts_context_lower(self):
        stack = [
            ["file.py", 10, "level4", "level4"],
            ["file.py", 11, "level5", "level5"],
        ]
        profile = {
            "init_stack_trace": [
                ["file.py", 1, "level0", "level0"],
                ["file.py", 1, "level1", "level1"],
                ["file.py", 1, "level2", "level2"],
                ["file.py", 1, "level3", "level3"],
            ],
            "result": [
                {
                    "start": 2.0,
                    "exec_context": ((2, {"a": "1"}), (6, {"b": "1"})),
                    "stack": list(stack),
                },
                {
                    "start": 10.35,
                    "exec_context": (),
                    "stack": None,
                },
            ],
        }
        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=False)
        res = sp.prepare_document()
        events = [
            (e["type"], res["shared"]["frames"][e["frame"]]["name"])
            for e in res["profiles"][0]["events"]
        ]
        self.assertEqual(
            events,
            [
                ("O", "level4"),
                ("O", "b=1"),
                ("O", "level5"),
                ("C", "level5"),
                ("C", "b=1"),
                ("C", "level4"),
            ],
        )

    def test_converts_no_context(self):
        stack = [
            ["file.py", 10, "level4", "level4"],
            ["file.py", 11, "level5", "level5"],
        ]
        profile = {
            "init_stack_trace": [
                ["file.py", 1, "level0", "level0"],
                ["file.py", 1, "level1", "level1"],
                ["file.py", 1, "level2", "level2"],
                ["file.py", 1, "level3", "level3"],
            ],
            "result": [
                {
                    "start": 2.0,
                    "exec_context": ((2, {"a": "1"}), (6, {"b": "1"})),
                    "stack": list(stack),
                },
                {
                    "start": 10.35,
                    "exec_context": (),
                    "stack": None,
                },
            ],
        }
        sp = Speedscope(init_stack_trace=profile["init_stack_trace"])
        sp.add("profile", profile["result"])
        sp.add_output(["profile"], complete=False, use_context=False)
        res = sp.prepare_document()
        events = [
            (e["type"], res["shared"]["frames"][e["frame"]]["name"])
            for e in res["profiles"][0]["events"]
        ]
        self.assertEqual(
            events,
            [
                ("O", "level4"),
                ("O", "level5"),
                ("C", "level5"),
                ("C", "level4"),
            ],
        )


@tagged("post_install", "-at_install", "profiling")
class TestProfiling(TransactionCase):
    def test_default_values(self):
        p = Profiler()
        self.assertEqual(p.db, self.env.cr.dbname)

    def test_sql_summary_after_entry_processing(self):
        with Profiler(db=None, collectors=["sql"]) as p:
            self.env.cr.execute("SELECT 1")
        collector = p.collectors[0]
        _ = collector.entries
        self.assertIn("sql", collector.summary())

    def test_traces_async_dedup_idle(self):
        with Profiler(
            db=None,
            collectors=["traces_async"],
            params={"traces_async_interval": 0.001},
        ) as p:
            time.sleep(0.4)
        self.assertLess(len(p.collectors[0].entries), 20)

    def test_env_profiler_database(self):
        p = Profiler(collectors=[])
        self.assertEqual(p.db, self.env.cr.dbname)

    def test_env_profiler_description(self):
        with Profiler(collectors=[], db=None) as p:
            self.assertIn("test_env_profiler_description", p.description)

    def test_execution_context_save(self):
        with Profiler(db=None, collectors=["sql"]) as p:
            for letter in ("a", "b"):
                stack_level = profiler.stack_size()
                with ExecutionContext(letter=letter):
                    self.env.cr.execute("SELECT 1")
        entries = p.collectors[0].entries
        self.assertEqual(
            entries.pop(0)["exec_context"], ((stack_level, {"letter": "a"}),)
        )
        self.assertEqual(
            entries.pop(0)["exec_context"], ((stack_level, {"letter": "b"}),)
        )

    def test_execution_context_nested(self):
        with Profiler(db=None, collectors=["sql"]) as p:
            stack_level = profiler.stack_size()
            with ExecutionContext(letter="a"):
                self.env.cr.execute("SELECT 1")
                with ExecutionContext(letter="b"):
                    self.env.cr.execute("SELECT 1")
                with ExecutionContext(letter="c"):
                    self.env.cr.execute("SELECT 1")
                self.env.cr.execute("SELECT 1")
        entries = p.collectors[0].entries
        self.assertEqual(
            entries.pop(0)["exec_context"], ((stack_level, {"letter": "a"}),)
        )
        self.assertEqual(
            entries.pop(0)["exec_context"],
            ((stack_level, {"letter": "a"}), (stack_level, {"letter": "b"})),
        )
        self.assertEqual(
            entries.pop(0)["exec_context"],
            ((stack_level, {"letter": "a"}), (stack_level, {"letter": "c"})),
        )
        self.assertEqual(
            entries.pop(0)["exec_context"], ((stack_level, {"letter": "a"}),)
        )

    def test_qweb_recorder(self):
        template = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "root",
                "arch_db": """<t t-name="root">
                <t t-foreach="{'a': 3, 'b': 2, 'c': 1}" t-as="item">
                    [<t t-out="item_index"/>: <t t-set="record" t-value="item"/><t t-call="base.dummy"/> <t t-out="item_value"/>]
                    <b t-out="add_one_query()"/></t>
            </t>""",
            }
        )
        child_template = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "type": "qweb",
                "key": "dummy",
                "arch_db": '<t t-name="dummy"><span t-attf-class="myclass"><t t-out="record"/> <t t-out="add_one_query()"/></span></t>',
            }
        )
        self.env.cr.execute(
            "INSERT INTO ir_model_data(name, model, res_id, module)VALUES ('dummy', 'ir.ui.view', %s, 'base')",
            [child_template.id],
        )

        values = {
            "add_one_query": lambda: (
                self.env.cr.execute("SELECT id FROM ir_ui_view LIMIT 1") or "query"
            )
        }
        result = """
                    [0: <span class="myclass">a query</span> 3]
                    <b>query</b>
                    [1: <span class="myclass">b query</span> 2]
                    <b>query</b>
                    [2: <span class="myclass">c query</span> 1]
                    <b>query</b>
        """

        rendered = self.env["ir.qweb"]._render(template.id, values)
        self.assertEqual(rendered.strip(), result.strip(), "Without profiling")

        with Profiler(description="test", collectors=["qweb"], db=None):
            self.env["ir.qweb"]._render(template.id, values)

        with Profiler(description="test", collectors=["qweb"], db=None) as p:
            rendered = self.env["ir.qweb"]._render(template.id, values)
            self.assertEqual(rendered.strip(), result.strip())

        self.assertEqual(
            p.collectors[0].entries[0]["results"]["archs"],
            {
                template.id: template.arch_db,
                child_template.id: child_template.arch_db,
            },
        )

        for data in p.collectors[0].entries[0]["results"]["data"]:
            data.pop("delay")

        data = p.collectors[0].entries[0]["results"]["data"]
        expected = [
            {
                "view_id": template.id,
                "xpath": "/t/t",
                "directive": """t-foreach="{'a': 3, 'b': 2, 'c': 1}" t-as='item'""",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[1]",
                "directive": "t-out='item_index'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[2]",
                "directive": "t-set='record' t-value='item'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[3]",
                "directive": "t-call='base.dummy'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span",
                "directive": "t-attf-class='myclass'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span/t[1]",
                "directive": "t-out='record'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span/t[2]",
                "directive": "t-out='add_one_query()'",
                "query": 1,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[4]",
                "directive": "t-out='item_value'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/b",
                "directive": "t-out='add_one_query()'",
                "query": 1,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[1]",
                "directive": "t-out='item_index'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[2]",
                "directive": "t-set='record' t-value='item'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[3]",
                "directive": "t-call='base.dummy'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span",
                "directive": "t-attf-class='myclass'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span/t[1]",
                "directive": "t-out='record'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span/t[2]",
                "directive": "t-out='add_one_query()'",
                "query": 1,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[4]",
                "directive": "t-out='item_value'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/b",
                "directive": "t-out='add_one_query()'",
                "query": 1,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[1]",
                "directive": "t-out='item_index'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[2]",
                "directive": "t-set='record' t-value='item'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[3]",
                "directive": "t-call='base.dummy'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span",
                "directive": "t-attf-class='myclass'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span/t[1]",
                "directive": "t-out='record'",
                "query": 0,
            },
            {
                "view_id": child_template.id,
                "xpath": "/t/span/t[2]",
                "directive": "t-out='add_one_query()'",
                "query": 1,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/t[4]",
                "directive": "t-out='item_value'",
                "query": 0,
            },
            {
                "view_id": template.id,
                "xpath": "/t/t/b",
                "directive": "t-out='add_one_query()'",
                "query": 1,
            },
        ]
        self.assertEqual(data, expected)

    def test_default_recorders(self):
        with Profiler(db=None) as p:
            queries_start = self.env.cr.sql_log_count  # noqa: E8516  asserts the row counter itself
            for i in range(10):
                self.env["res.partner"].create({"name": "snail%s" % i})
            self.env.flush_all()
            total_queries = self.env.cr.sql_log_count - queries_start  # noqa: E8516  asserts the row counter itself

        rq = next(r for r in p.collectors if r.name == "sql").entries
        self.assertEqual(p.init_stack_trace[-1][2], "test_default_recorders")
        self.assertEqual(p.init_stack_trace[-1][0].split("/")[-1], "test_profiler.py")

        self.assertEqual(len(rq), total_queries)
        first_query = rq[0]
        self.assertEqual(first_query["stack"][0][2], "create")

        self.assertGreater(first_query["time"], 0)
        self.assertEqual(first_query["stack"][-1][2], "_record_metrics")
        self.assertEqual(first_query["stack"][-1][0].split("/")[-1], "metrics.py")

    def test_profiler_return(self):
        self.registry_enter_test_mode()
        self.startClassPatcher(patch("odoo.db.db_connect", return_value=self.registry))
        with self.profile(collectors=["sql"]) as p:
            self.env.cr.execute("SELECT 1")
        self.assertEqual(p.collectors[0].entries[0]["query"], "SELECT 1")


def deep_call(func, depth):
    if depth > 0:
        deep_call(func, depth - 1)
    else:
        func()


@tagged("-standard", "profiling_performance")
class TestPerformance(BaseCase):
    def test_collector_max_frequency(self):
        collector = profiler.Collector()
        p = Profiler(collectors=[collector], db=None)

        def collect():
            collector.add()

        with p:
            start = time.time()
            while start + 1 > time.time():
                deep_call(collect, 20)

        self.assertGreater(len(collector.entries), 20000)

        collector = profiler.Collector()
        p = Profiler(collectors=[collector], db=None)

        def collect_1_s():
            start = time.time()
            while start + 1 > time.time():
                collector.add()

        with p:
            deep_call(collect_1_s, 20)

        self.assertGreater(len(collector.entries), 50000)

    def test_frequencies_1ms_sleep(self):

        def sleep_1():
            time.sleep(0.0001)

        def sleep_2():
            time.sleep(0.0001)

        with Profiler(collectors=["traces_async"], db=None) as res:
            start = time.time()
            while start + 1 > time.time():
                sleep_1()
                sleep_2()

        entry_count = len(res.collectors[0].entries)
        self.assertGreater(entry_count, 700)

    def test_traces_async_memory_optimisation(self):
        with Profiler(collectors=["traces_async"], db=None) as res:
            time.sleep(1)
        entry_count = len(res.collectors[0].entries)
        self.assertLess(entry_count, 5)


@tagged("-standard", "profiling")
class TestSyncRecorder(BaseCase):
    def test_sync_recorder(self):
        if sys.gettrace() is not None:
            self.skipTest(
                f"Cannot start SyncCollector, settrace already set: {sys.gettrace()}"
            )

        def a():
            b()
            c()

        def b():
            pass

        def c():
            d()
            d()

        def d():
            pass

        with Profiler(description="test", collectors=["traces_sync"], db=None) as p:
            a()

        stacks = [r["stack"] for r in p.collectors[0].entries]

        stacks_methods = [[frame[2] for frame in stack] for stack in stacks]
        self.assertEqual(
            stacks_methods,
            [
                ["a"],
                ["a", "b"],
                ["a"],
                ["a", "c"],
                ["a", "c", "d"],
                ["a", "c"],
                ["a", "c", "d"],
                ["a", "c"],
                ["a"],
                [],
            ],
        )

        stacks_lines = [[frame[1] for frame in stack] for stack in stacks]
        self.assertEqual(
            stacks_lines[1][0] + 1,
            stacks_lines[3][0],
            "Call of b() in a() should be one line before call of c()",
        )


@tagged("-standard", "profiling_memory")
class TestMemoryProfiler(HttpCase):
    def test_memory_profiler(self):
        with Profiler(collectors=["memory"], db=None):
            self.env["base.module.update"].create({}).update_module()


class _FakeRequest:
    def __init__(self):
        self.session = {}


@tagged("post_install", "-at_install", "profiling")
class TestProfilingStateMachine(TransactionCase):
    def _set_window(self, value):
        self.env["ir.config_parameter"].sudo().set_param(
            "base.profiling_enabled_until", value
        )

    def test_enabled_until_blank_is_none(self):
        self._set_window(False)
        self.assertIsNone(self.env["ir.profile"]._get_enabled_until())

    def test_enabled_until_expired_is_none(self):
        self._set_window("2000-01-01 00:00:00")
        self.assertIsNone(self.env["ir.profile"]._get_enabled_until())

    def test_enabled_until_future_returns_limit(self):
        self._set_window("2999-01-01 00:00:00")
        self.assertEqual(
            self.env["ir.profile"]._get_enabled_until(), "2999-01-01 00:00:00"
        )

    def test_non_system_cannot_arm_profiling(self):
        self._set_window(False)
        user = new_test_user(self.env, login="noArmProfiling", groups="base.group_user")
        fake_request = _FakeRequest()
        with patch("odoo.addons.base.models.ir_profile.request", fake_request):
            with self.assertRaises(UserError):
                self.env["ir.profile"].with_user(user).set_profiling(True)
        self.assertIsNone(fake_request.session.get("profile_session"))

    def test_system_user_gets_wizard_when_unarmed(self):
        self._set_window(False)
        fake_request = _FakeRequest()
        with patch("odoo.addons.base.models.ir_profile.request", fake_request):
            action = self.env["ir.profile"].set_profiling(True)
        self.assertEqual(action["res_model"], "base.enable.profiling.wizard")

    def test_parse_params_memory_limit_non_numeric(self):
        IrProfile = self.env["ir.profile"]
        self.assertEqual(
            IrProfile._parse_params({"memory_limit": "abc"})["memory_limit"], 0
        )
        self.assertEqual(
            IrProfile._parse_params({"memory_limit": None})["memory_limit"], 0
        )
        self.assertEqual(
            IrProfile._parse_params({"memory_limit": "42"})["memory_limit"], 42
        )
        self.assertEqual(IrProfile._parse_params({})["memory_limit"], 0)

    def test_parse_params_malformed_values_degrade_to_defaults(self):
        IrProfile = self.env["ir.profile"]
        params = IrProfile._parse_params(
            {
                "constant_time": "x",
                "aggregate_sql": "junk",
                "use_execution_context": "??",
                "combined_profile": "x",
                "sql_no_gap_profile": "x",
                "sql_density_profile": "x",
                "frames_profile": "x",
                "profile_aggregation_mode": "evil",
                "memory_limit": "NaN",
            }
        )
        self.assertFalse(params["constant_time"])
        self.assertFalse(params["aggregate_sql"])
        self.assertTrue(params["use_context"], "use_execution_context defaults True")
        self.assertFalse(params["combined_profile"])
        self.assertFalse(params["sql_no_gap_profile"])
        self.assertFalse(params["sql_density_profile"])
        self.assertFalse(params["frames_profile"])
        self.assertEqual(params["profile_aggregation_mode"], "tabs")
        self.assertEqual(params["memory_limit"], 0)

    def test_parse_params_valid_values_pass_through(self):
        IrProfile = self.env["ir.profile"]
        params = IrProfile._parse_params(
            {
                "constant_time": "1",
                "use_execution_context": "0",
                "profile_aggregation_mode": "temporal",
            }
        )
        self.assertTrue(params["constant_time"])
        self.assertFalse(params["use_context"])
        self.assertEqual(params["profile_aggregation_mode"], "temporal")
