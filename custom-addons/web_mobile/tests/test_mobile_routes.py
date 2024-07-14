# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from PIL import Image
from io import BytesIO
from uuid import uuid4
from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged, get_db_name
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tools import config, mute_logger


@tagged("-at_install", "post_install")
class MobileRoutesTest(HttpCaseWithUserDemo):
    """
    This test suite is used to request the routes used by the mobile applications (Android & iOS)
    """

    def setUp(self):
        super().setUp()
        self.headers = {
            "Content-Type": "application/json",
        }

    def test_version_info(self):
        """
        This request is used to check for a compatible Odoo server
        """
        payload = self._build_payload()
        response = self.url_open(
            "/web/webclient/version_info",
            data=json.dumps(payload),
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._is_success_json_response(data)
        result = data["result"]
        self.assertIn("server_version_info", result)
        self.assertIsInstance(result["server_version_info"], list)
        self.assertGreater(len(result["server_version_info"]), 0)
        self.assertEqual(result["server_version_info"][-1], "e")

    @mute_logger("odoo.http")
    def test_database_list(self):
        """
        This request is used to retrieve the databases' list
        NB: this route has a different behavior depending on the ability to list databases or not.
        """
        payload = self._build_payload()
        response = self.url_open("/web/database/list", data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if config['list_db']:
            self._is_success_json_response(data)
            result = data["result"]
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIn(self.env.cr.dbname, result)
        else:
            self._is_error_json_response(data)
            error = data["error"]
            self.assertEqual(error["code"], 200)
            self.assertEqual(error["message"], "Odoo Server Error")
            self.assertEqual(error["data"]["name"], "odoo.exceptions.AccessDenied")

    def test_authenticate(self):
        """
        This request is used to authenticate a user using its username/password
        and retrieve its details & session's id
        """
        payload = self._build_payload({
            "db": get_db_name(),
            "login": "demo",
            "password": "demo",
        })
        response = self.url_open("/web/session/authenticate", data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._is_success_json_response(data)
        result = data["result"]
        self.assertIsInstance(response.cookies.get("session_id"), str, "should have a session cookie")
        self.assertEqual(result["username"], "demo")
        self.assertEqual(result["db"], self.env.cr.dbname)
        user = self.env["res.users"].search_read([("login", "=", "demo")], limit=1)[0]
        self.assertEqual(result["uid"], user["id"])
        self.assertEqual(result["name"], user["name"])

    @mute_logger("odoo.http")
    def test_authenticate_wrong_credentials(self):
        """
        This request is used to attempt to authenticate a user using the wrong credentials
        (username/password) and check the returned error
        """
        payload = self._build_payload({
            "db": self.env.cr.dbname,
            "login": "demo",
            "password": "admin",
        })
        response = self.url_open("/web/session/authenticate", data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._is_error_json_response(data)
        error = data["error"]
        self.assertEqual(error["code"], 200)
        self.assertEqual(error["message"], "Odoo Server Error")
        self.assertEqual(error["data"]["name"], "odoo.exceptions.AccessDenied")

    @mute_logger("odoo.http")
    def test_authenticate_wrong_database(self):
        """
        This request is used to authenticate a user against a non existing database and
        check the returned error
        """
        db_name = "dummydb-%s" % str(uuid4())
        payload = self._build_payload({
            "db": db_name,
            "login": "demo",
            "password": "admin",
        })
        response = self.url_open("/web/session/authenticate", data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._is_error_json_response(data)
        error = data["error"]
        self.assertEqual(error["code"], 200)
        self.assertEqual(error["message"], "Odoo Server Error")
        self.assertEqual(error["data"]["name"], "odoo.exceptions.AccessError")

    def test_avatar(self):
        """
        This request is used to retrieve the user's picture
        """
        self.authenticate("demo", "demo")
        self.user_demo.image_1920 = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        response = self.url_open("/web/image?model=res.users&field=image_medium&id=%s" % self.session.uid)
        self.assertEqual(response.status_code, 200)
        avatar = Image.open(BytesIO(response.content))
        self.assertIsInstance(avatar, Image.Image)

    def test_session_info(self):
        """
        This request is used to authenticate a user using its session id
        """
        payload = self._build_payload()
        self.authenticate("demo", "demo")
        response = self.url_open("/web/session/get_session_info", data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._is_success_json_response(data)
        result = data["result"]
        self.assertEqual(result["username"], "demo")
        self.assertEqual(result["db"], self.env.cr.dbname)
        self.assertEqual(result["uid"], self.session.uid)

    def _build_payload(self, params={}):
        """
        Helper to properly build jsonrpc payload
        """
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "id": str(uuid4()),
            "params": params,
        }

    def _is_success_json_response(self, data):
        """"
        Helper to validate a standard JSONRPC response's structure
        """
        self.assertEqual(list(data.keys()), ["jsonrpc", "id", "result"], "should be a valid jsonrpc response")
        self.assertTrue(isinstance(data["jsonrpc"], str))
        self.assertTrue(isinstance(data["id"], str))

    def _is_error_json_response(self, data):
        """
        Helper to validate an error JSONRPC response's structure
        """
        self.assertEqual(list(data.keys()), ["jsonrpc", "id", "error"], "should be a valid error jsonrpc response")
        self.assertTrue(isinstance(data["jsonrpc"], str))
        self.assertTrue(isinstance(data["id"], str))
        self.assertTrue(isinstance(data["error"], dict))
        self.assertEqual(list(data["error"].keys()), ["code", "message", "data"], "should be a valid error structure")
        error = data["error"]
        self.assertTrue(isinstance(error["data"], dict))
        self.assertIn("name", error["data"])
        self.assertIn("message", error["data"])


@tagged("-at_install", "post_install")
class MobileRoutesMultidbTest(MobileRoutesTest):

    def run(self, result=None):
        if not config['list_db']:
            return
        dblist = (get_db_name(), 'another_database')
        assert len(dblist) >= 2, "There should be at least 2 databases"
        with patch('odoo.http.db_list') as db_list, \
             patch('odoo.http.db_filter') as db_filter, \
             patch('odoo.http.Registry') as Registry:
            db_list.return_value = dblist
            db_filter.side_effect = lambda dbs, host=None: [db for db in dbs if db in dblist]
            Registry.return_value = self.registry
            return super().run(result)
