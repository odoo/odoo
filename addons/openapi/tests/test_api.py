# Copyright 2018-2019 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2018 Rafis Bikbov <https://it-projects.info/team/bikbov>
# Copyright 2019 Anvar Kildebekov <https://it-projects.info/team/fedoranvar>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import logging

import requests

from odoo import api
from odoo.tests import tagged
from odoo.tests.common import PORT, HttpCase, get_db_name

from ..controllers import pinguin

_logger = logging.getLogger(__name__)

USER_DEMO = "base.user_demo"
USER_ADMIN = "base.user_root"
MESSAGE = "message is posted from API"


# TODO: test other methods:
# * /res.partner/call/{method_name} (without recordset)
# * /res.partner/{record_id}


@tagged("post_install", "at_install")
class TestAPI(HttpCase):
    def setUp(self):
        super(TestAPI, self).setUp()
        self.db_name = get_db_name()
        self.phantom_env = api.Environment(self.registry.test_cr, self.uid, {})
        self.demo_user = self.phantom_env.ref(USER_DEMO)
        self.admin_user = self.phantom_env.ref(USER_ADMIN)
        self.model_name = "res.partner"

    def request(self, method, url, auth=None, **kwargs):
        kwargs.setdefault("model", self.model_name)
        kwargs.setdefault("namespace", "demo")
        url = ("http://localhost:%d/api/v1/{namespace}" % PORT + url).format(**kwargs)
        self.opener = requests.Session()
        self.opener.cookies["session_id"] = self.session_id
        return self.opener.request(
            method, url, timeout=30, auth=auth, json=kwargs.get("data_json")
        )

    def request_from_user(self, user, *args, **kwargs):
        kwargs["auth"] = requests.auth.HTTPBasicAuth(self.db_name, user.openapi_token)
        return self.request(*args, **kwargs)

    def test_read_many_all(self):
        resp = self.request_from_user(self.demo_user, "GET", "/{model}")
        self.assertEqual(resp.status_code, pinguin.CODE__success)
        # TODO check content

    def test_read_one(self):
        record_id = self.phantom_env[self.model_name].search([], limit=1).id
        resp = self.request_from_user(
            self.demo_user, "GET", "/{model}/{record_id}", record_id=record_id
        )
        self.assertEqual(resp.status_code, pinguin.CODE__success)
        # TODO check content

    def test_create_one(self):
        data_for_create = {"name": "created_from_test", "type": "other"}
        resp = self.request_from_user(
            self.demo_user, "POST", "/{model}", data_json=data_for_create
        )
        self.assertEqual(resp.status_code, pinguin.CODE__created)
        created_user = self.phantom_env[self.model_name].browse(resp.json()["id"])
        self.assertEqual(created_user.name, data_for_create["name"])

    # TODO: doesn't work in test environment
    def _test_create_one_with_invalid_data(self):
        """create partner without name"""
        self.phantom_env = api.Environment(self.registry.test_cr, self.uid, {})
        data_for_create = {"email": "string"}
        resp = self.request_from_user(
            self.demo_user, "POST", "/{model}", data_json=data_for_create
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_one(self):
        data_for_update = {
            "name": "for update in test",
        }
        partner = self.phantom_env[self.model_name].search([], limit=1)
        resp = self.request_from_user(
            self.demo_user,
            "PUT",
            "/{model}/{record_id}",
            record_id=partner.id,
            data_json=data_for_update,
        )
        self.assertEqual(resp.status_code, pinguin.CODE__ok_no_content)
        self.assertEqual(partner.name, data_for_update["name"])
        # TODO: check result

    # TODO: doesn't work in test environment
    def _test_unlink_one(self):
        partner = self.phantom_env[self.model_name].create(
            {"name": "record for deleting from test"}
        )
        resp = self.request_from_user(
            self.demo_user, "DELETE", "/{model}/{record_id}", record_id=partner.id
        )
        self.assertEqual(resp.status_code, pinguin.CODE__ok_no_content)
        self.assertFalse(self.phantom_env[self.model_name].browse(partner.id).exists())
        # TODO: check result

    def test_unauthorized_user(self):
        resp = self.request("GET", "/{model}")
        self.assertEqual(resp.status_code, pinguin.CODE__no_user_auth[0])

    # TODO: doesn't work in test environment
    def _test_invalid_dbname(self):
        db_name = "invalid_db_name"
        resp = self.request(
            "GET",
            "/{model}",
            auth=requests.auth.HTTPBasicAuth(db_name, self.demo_user.openapi_token),
        )
        self.assertEqual(resp.status_code, pinguin.CODE__db_not_found[0])
        self.assertEqual(resp.json()["error"], pinguin.CODE__db_not_found[1])

    def test_invalid_user_token(self):
        invalid_token = "invalid_user_token"
        resp = self.request(
            "GET",
            "/{model}",
            auth=requests.auth.HTTPBasicAuth(self.db_name, invalid_token),
        )
        self.assertEqual(resp.status_code, pinguin.CODE__no_user_auth[0])
        self.assertEqual(resp.json()["error"], pinguin.CODE__no_user_auth[1])

    def test_user_not_allowed_for_namespace(self):
        namespace = self.phantom_env["openapi.namespace"].search(
            [("name", "=", "demo")]
        )
        new_user = self.phantom_env["res.users"].create(
            {"name": "new user", "login": "new_user"}
        )
        new_user.write(
            {"groups_id": [(4, self.phantom_env.ref("openapi.group_user").id)]}
        )
        new_user.reset_openapi_token()
        new_user.flush()
        self.assertTrue(new_user.id not in namespace.user_ids.ids)
        self.assertTrue(namespace.id not in new_user.namespace_ids.ids)

        resp = self.request_from_user(new_user, "GET", "/{model}")
        self.assertEqual(resp.status_code, pinguin.CODE__user_no_perm[0], resp.json())
        self.assertEqual(resp.json()["error"], pinguin.CODE__user_no_perm[1])

    def test_call_allowed_method_on_singleton_record(self):
        if (
            not self.env["ir.module.module"].search([("name", "=", "mail")]).state
            == "installed"
        ):
            self.skipTest(
                "To run test 'test_call_allowed_method_on_singleton_record' install 'mail'-module"
            )
        partner = self.phantom_env[self.model_name].search([], limit=1)
        method_name = "message_post"
        method_params = {"kwargs": {"body": MESSAGE}}
        resp = self.request_from_user(
            self.demo_user,
            "PATCH",
            "/{model}/{record_id}/call/{method_name}",
            record_id=partner.id,
            method_name=method_name,
            data_json=method_params,
        )
        self.assertEqual(resp.status_code, pinguin.CODE__success)
        # TODO check that message is created

    def test_call_allowed_method_on_recordset(self):
        partners = self.phantom_env[self.model_name].search([], limit=5)
        method_name = "write"
        method_params = {
            "args": [{"name": "changed from write method called from api"}],
        }
        ids = partners.mapped("id")
        ids_str = ",".join(str(i) for i in ids)

        resp = self.request_from_user(
            self.demo_user,
            "PATCH",
            "/{model}/call/{method_name}/{ids}",
            method_name=method_name,
            ids=ids_str,
            data_json=method_params,
        )

        self.assertEqual(resp.status_code, pinguin.CODE__success)
        for i in range(len(partners)):
            self.assertTrue(resp.json()[i])
        # reread records
        partners = self.phantom_env[self.model_name].browse(ids)
        for partner in partners:
            self.assertEqual(partner.name, method_params["args"][0]["name"])

    def test_call_model_method(self):
        domain = [["id", "=", 1]]
        record = self.phantom_env[self.model_name].search(domain)
        self.assertTrue(record, "Record with ID 1 is not available")

        method_name = "search"
        method_params = {
            "args": [domain],
        }
        resp = self.request_from_user(
            self.demo_user,
            "PATCH",
            "/{model}/call/{method_name}",
            method_name=method_name,
            data_json=method_params,
        )

        self.assertEqual(resp.status_code, pinguin.CODE__success)
        self.assertEqual(resp.json(), [1])

    # TODO: doesn't work in test environment
    def _test_log_creating(self):
        logs_count_before_request = len(self.phantom_env["openapi.log"].search([]))
        self.request_from_user(self.demo_user, "GET", "/{model}")
        logs_count_after_request = len(self.phantom_env["openapi.log"].search([]))
        self.assertTrue(logs_count_after_request > logs_count_before_request)

    # TODO test is not update for the latest module version
    def _test_get_report_for_allowed_model(self):
        super_user = self.phantom_env.ref(USER_ADMIN)
        modelname_for_report = "ir.module.module"
        report_external_id = "base.ir_module_reference_print"

        model_for_report = self.phantom_env["ir.model"].search(
            [("model", "=", modelname_for_report)]
        )
        namespace = self.phantom_env["openapi.namespace"].search([("name", "=")])
        records_for_report = self.phantom_env[modelname_for_report].search([], limit=3)
        docids = ",".join([str(i) for i in records_for_report.ids])

        self.phantom_env["openapi.access"].create(
            {
                "active": True,
                "namespace_id": namespace.id,
                "model_id": model_for_report.id,
                "model": modelname_for_report,
                "api_create": False,
                "api_read": True,
                "api_update": False,
                "api_public_methods": False,
                "public_methods": False,
                "private_methods": False,
                "read_one_id": False,
                "read_many_id": False,
                "create_context_ids": False,
            }
        )

        super_user.write({"namespace_ids": [(4, namespace.id)]})

        url = "http://localhost:%d/api/v1/demo/report/html/%s/%s" % (
            PORT,
            report_external_id,
            docids,
        )
        resp = requests.request(
            "GET",
            url,
            timeout=30,
            auth=requests.auth.HTTPBasicAuth(self.db_name, super_user.openapi_token),
        )
        self.assertEqual(resp.status_code, pinguin.CODE__success)

    def test_response_has_no_error(self):
        method_name = "search_read"
        method_params = {
            "args": [[["id", "=", "1"]]],
        }
        resp = self.request_from_user(
            self.demo_user,
            "PATCH",
            "/{model}/call/{method_name}",
            method_name=method_name,
            data_json=method_params,
        )
        self.assertNotIn("error", resp.json())
