from functools import partial
from xmlrpc.client import Fault

from odoo import http
from odoo.tests import common, tagged
from odoo.tools.misc import mute_logger


@tagged('-at_install', 'post_install')
class TestError(common.HttpCase):
    def setUp(self):
        super(TestError, self).setUp()
        uid = self.ref("base.user_admin")
        self.rpc = partial(self.xmlrpc_object.execute, common.get_db_name(), uid, "admin")

        # Reset the admin's lang to avoid breaking tests due to admin not in English
        self.rpc("res.users", "write", [uid], {"lang": False})

    def test_01_create(self):
        """ Create: mandatory field not provided """
        self.rpc("test_rpc.model_b", "create", {"name": "B1"})
        with self.assertRaises(Fault) as ctx, mute_logger("odoo.sql_db", "odoo.http"):
            self.rpc("test_rpc.model_b", "create", {})

        e = ctx.exception
        self.assertIn("The operation cannot be completed:", e.faultString)
        self.assertIn("create/update: a mandatory field is not set", e.faultString)
        self.assertIn(
            "delete: another model requires the record being deleted",
            e.faultString,
        )
        self.assertIn("Model: 'Model B' (test_rpc.model_b)", e.faultString)
        self.assertIn("field 'Name' (name)", e.faultString)

    def test_02_delete(self):
        """ Delete: NOT NULL and ON DELETE RESTRICT constraints """
        b1 = self.rpc("test_rpc.model_b", "create", {"name": "B1"})
        b2 = self.rpc("test_rpc.model_b", "create", {"name": "B2"})
        self.rpc("test_rpc.model_a", "create", {"name": "A1", "field_b1": b1, "field_b2": b2})

        with self.assertRaises(Fault) as ctx, mute_logger("odoo.sql_db", "odoo.http"):
            self.rpc("test_rpc.model_b", "unlink", b1)

        e = ctx.exception
        self.assertIn("The operation cannot be completed:", e.faultString)
        self.assertIn(
            "Another model requires the record being deleted, if possible, archive it instead",
            e.faultString,
        )
        self.assertIn("Model: 'Model A' (test_rpc.model_a)", e.faultString)
        self.assertIn("Foreign key: 'required field'", e.faultString)

        # Unlink b2 => ON DELETE RESTRICT constraint raises
        with self.assertRaises(Fault) as ctx, mute_logger("odoo.sql_db", "odoo.http"):
            self.rpc("test_rpc.model_b", "unlink", b2)

        e = ctx.exception
        self.assertIn("The operation cannot be completed:", e.faultString)
        self.assertIn(
            "Another model requires the record being deleted, if possible, archive it instead",
            e.faultString,
        )
        self.assertIn("Model: 'Model A' (test_rpc.model_a)", e.faultString)
        self.assertIn("Foreign key: 'restricted field'", e.faultString)

    def test_03_sql_constraint(self):
        with mute_logger("odoo.sql_db"), self.assertLogs("odoo.http", level="WARNING") as capture:
            with self.assertRaisesRegex(Fault, r'The operation cannot be completed: The value must be positive'):
                self.rpc("test_rpc.model_b", "create", {"name": "B1", "value": -1})
            self.assertEqual(len(capture.output), 1)

    def test_04_multi_db(self):
        def db_list(**kwargs):
            return [self.env.cr.dbname, self.env.cr.dbname + '_another_db']
        self.patch(http, 'db_list', db_list)  # this is just to ensure that the request won't have a db, breaking monodb behaviour

        self.rpc("test_rpc.model_b", "create", {"name": "B1"})
