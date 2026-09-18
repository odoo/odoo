from odoo.libs.json import dumps as json_dumps
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "web_http", "web_action")
class TestLoadBreadcrumbs(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env["ir.model"]._get_id("res.partner")

        cls.env = cls.env(user=cls.env.ref("base.user_admin"))
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )

        cls.window_action = cls.env["ir.actions.act_window"].create(
            {
                "name": "Test Partners",
                "res_model": "res.partner",
            }
        )

        cls.server_action_without_path = cls.env["ir.actions.server"].create(
            {
                "name": "Test Server Action Without Path",
                "model_id": model_id,
                "state": "code",
                "code": """action = {
                'type': 'ir.actions.act_window',
                'name': 'Window Action From Server',
                'res_model': 'res.partner',
            }""",
            }
        )

        cls.server_action = cls.env["ir.actions.server"].create(
            {
                "name": "Breadcrumb Server Action",
                "model_id": model_id,
                "state": "code",
                "path": "test_path",
                "code": """action = {
                'type': 'ir.actions.act_window',
                'name': 'Window Action From Server',
                'res_model': 'res.partner',
                'views': [(False, 'list')],
            }""",
            }
        )

        cls.client_action = cls.env["ir.actions.client"].create(
            {
                "name": "Breadcrumb Client Action",
                "res_model": "res.partner",
                "tag": "account_report",
            }
        )

        cls.server_action_returning_nothing = cls.env["ir.actions.server"].create(
            {
                "name": "Breadcrumb Server Action Returning Nothing",
                "model_id": model_id,
                "state": "code",
                "path": "test_path_no_return",
                "code": "action = False",
            }
        )

        cls.server_action_with_form_view = cls.env["ir.actions.server"].create(
            {
                "name": "Breadcrumb Server Action With Path",
                "model_id": model_id,
                "state": "code",
                "path": "test_path_form_view",
                "code": """action = {
                'type': 'ir.actions.act_window',
                'name': 'Window Action From Server',
                'res_model': 'res.partner',
                'views': [(False, 'form')],
            }""",
            }
        )

    def test_breadcrumbs_empty_action(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [],
                    },
                }
            ),
        )
        self.assertEqual(resp.json()["result"], [])

    def test_breadcrumbs_window_action(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.window_action.id,
                                "resId": None,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(resp.json()["result"][0]["display_name"], "Test Partners")

    def test_breadcrumbs_server_action_path(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.server_action_without_path.id,
                                "resId": None,
                            },
                            {
                                "action": self.server_action.id,
                                "resId": None,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(
            resp.json()["result"][0]["error"],
            "A server action must have a path to be restored",
        )
        self.assertEqual(
            resp.json()["result"][1]["display_name"],
            "Window Action From Server",
        )

    def test_breadcrumbs_client_action(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.client_action.id,
                                "resId": None,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(
            resp.json()["result"][0]["display_name"], "Breadcrumb Client Action"
        )

    def test_breadcrumbs_client_action_multirecord(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.client_action.id,
                                "resId": None,
                            },
                            {
                                "action": self.client_action.id,
                                "resId": 1,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(
            resp.json()["result"][0]["error"],
            "Client actions don't have multi-record views",
        )

    def test_breadcrumbs_action_with_res_model(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.client_action.id,
                                "resId": "new",
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(resp.json()["result"][0]["display_name"], "New")

        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.client_action.id,
                                "resId": self.partner.id,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(resp.json()["result"][0]["display_name"], "Test Partner")

    def test_breadcrumbs_server_action_without_res_model(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.server_action.id,
                                "resId": None,
                            },
                            {
                                "action": self.server_action_with_form_view.id,
                                "resId": None,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(
            resp.json()["result"][0]["display_name"],
            "Window Action From Server",
        )
        self.assertEqual(resp.json()["result"][1]["display_name"], None)

    def test_breadcrumbs_server_action_returning_nothing(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "action": self.server_action_returning_nothing.id,
                                "resId": None,
                            },
                            {
                                "action": self.window_action.id,
                                "resId": None,
                            },
                        ],
                    },
                }
            ),
        )
        result = resp.json()["result"]
        self.assertEqual(
            result[0]["error"],
            "Server action did not return a restorable action",
        )
        self.assertEqual(result[1]["display_name"], "Test Partners")

    def test_breadcrumbs_get_model(self):
        self.authenticate("admin", "admin")

        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "resId": None,
                                "model": "res.users",
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(resp.json()["error"]["message"], "Odoo Server Error")

        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "resId": self.partner.id,
                                "model": "res.partner",
                            },
                            {
                                "resId": "new",
                                "model": "res.partner",
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(
            resp.json()["result"][0]["display_name"], self.partner.display_name
        )
        self.assertEqual(resp.json()["result"][1]["display_name"], "New")

    def test_breadcrumbs_no_action_nor_model(self):
        self.authenticate("admin", "admin")
        resp = self.url_open(
            "/web/action/load_breadcrumbs",
            headers={"Content-Type": "application/json"},
            data=json_dumps(
                {
                    "params": {
                        "actions": [
                            {
                                "resId": None,
                            },
                        ],
                    },
                }
            ),
        )
        self.assertEqual(resp.json()["error"]["message"], "Odoo Server Error")


@tagged("post_install", "-at_install", "web_http", "web_action")
class TestLoadAudit(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.users"].create(
            {
                "name": "load audit",
                "login": "load_audit",
                "password": "load_audit_pw",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.restricted = cls.env["ir.actions.act_window"].create(
            {
                "name": "restricted",
                "res_model": "res.partner",
                "group_ids": [(6, 0, [cls.env.ref("base.group_system").id])],
            }
        )

    def _load(self, action_id):
        return self.url_open(
            "/web/action/load",
            headers={"Content-Type": "application/json"},
            data=json_dumps({"params": {"action_id": action_id}}),
        ).json()

    def test_a_restricted_action_is_refused_as_if_it_did_not_exist(self):
        self.authenticate("load_audit", "load_audit_pw")
        with self.assertLogs(
            "odoo.addons.base.models.ir_actions_actions", level="INFO"
        ) as captured:
            body = self._load(self.restricted.id)
        self.assertNotIn("result", body)
        missing = self._load(self.restricted.id + 100000)["error"]["data"]
        refused = body["error"]["data"]
        self.assertEqual(refused["name"], missing["name"])
        self.assertIn("does not exist", refused["message"])
        self.assertTrue(
            any("refused" in line and "groups" in line for line in captured.output)
        )

    def test_a_member_loads_the_restricted_action(self):
        self.authenticate("admin", "admin")
        self.assertEqual(
            self._load(self.restricted.id)["result"]["id"], self.restricted.id
        )

    def test_an_unreadable_target_model_is_refused_the_same_way(self):
        closed = self.env["ir.actions.act_window"].create(
            {"name": "closed", "res_model": "ir.config_parameter"}
        )
        self.authenticate("load_audit", "load_audit_pw")
        body = self._load(closed.id)
        self.assertIn("does not exist", body["error"]["data"]["message"])
