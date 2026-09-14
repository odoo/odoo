from odoo.tests import HttpCase, tagged

_NAV_HEADERS = {
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
}


@tagged("post_install", "-at_install", "web_http")
class TestJsonExportRoute(HttpCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param("web.json.enabled", "1")
        self.env.ref("base.user_admin").group_ids |= self.env.ref(
            "base.group_allow_export"
        )
        self.authenticate("admin", "admin")

    def _json(self, query):
        return self.url_open(
            f"/json/1/action-base.action_partner_form?{query}",
            headers=_NAV_HEADERS,
        )

    def test_non_aggregatable_field_is_client_error_not_500(self):
        resp = self._json("groupby=type&fields=name")
        self.assertEqual(
            resp.status_code,
            400,
            f"expected 400 for a non-aggregatable measure, got {resp.status_code}: "
            f"{resp.text[:300]}",
        )
        self.assertIn("not aggregatable", resp.text)

    def test_grouped_count_still_works(self):
        resp = self._json("groupby=type")
        self.assertEqual(
            resp.status_code,
            200,
            f"grouped __count read should succeed, got {resp.status_code}: "
            f"{resp.text[:300]}",
        )

    def _create_server_action(self, path, code):
        return self.env["ir.actions.server"].create(
            {
                "name": path,
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "code",
                "path": path,
                "code": code,
            }
        )

    def test_server_action_path_runs_on_a_read_only_transaction(self):
        self._create_server_action(
            "json_probe_list",
            "action = {'type': 'ir.actions.act_window', 'res_model': 'res.partner',"
            " 'view_mode': 'list', 'name': 'probe'}",
        )
        resp = self.url_open("/json/1/json_probe_list", headers=_NAV_HEADERS)
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        self.assertIn("records", resp.json())

    def test_server_action_that_writes_is_refused_not_500(self):
        self._create_server_action(
            "json_probe_write",
            "env['res.partner'].create({'name': 'must not land'})\n"
            "action = {'type': 'ir.actions.act_window', 'res_model': 'res.partner',"
            " 'view_mode': 'list', 'name': 'probe'}",
        )
        with self.assertLogs("odoo.http", level="WARNING"):
            resp = self.url_open("/json/1/json_probe_write", headers=_NAV_HEADERS)
        self.assertEqual(resp.status_code, 403, resp.text[:300])
        self.assertFalse(
            self.env["res.partner"].search_count([("name", "=", "must not land")])
        )

    def test_server_action_returning_no_action_is_a_client_error(self):
        self._create_server_action("json_probe_none", "x = 1")
        resp = self.url_open("/json/1/json_probe_none", headers=_NAV_HEADERS)
        self.assertEqual(resp.status_code, 400, resp.text[:300])

    def test_a_listing_with_defaults_left_out_is_redirected_to_its_canonical_url(self):
        resp = self.url_open(
            "/json/1/action-base.action_partner_form",
            headers=_NAV_HEADERS,
            allow_redirects=False,
        )
        self.assertEqual(resp.status_code, 307, resp.text[:300])
        location = resp.headers["Location"]
        self.assertIn("offset=0", location)
        self.assertIn("limit=", location)
        resp = self.url_open(location, headers=_NAV_HEADERS, allow_redirects=False)
        self.assertEqual(resp.status_code, 200, resp.text[:300])

    def test_a_record_read_is_never_redirected(self):
        partner = self.env.ref("base.partner_admin")
        resp = self.url_open(
            f"/json/1/action-base.action_partner_form/{partner.id}",
            headers=_NAV_HEADERS,
            allow_redirects=False,
        )
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        self.assertEqual(resp.json()["id"], partner.id)
