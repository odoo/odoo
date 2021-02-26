# -*- coding: utf-8 -*-

from functools import partial
from xmlrpc.client import ServerProxy

from odoo.tests import common, tagged, Transport
from odoo.tools.misc import mute_logger


@tagged('-at_install', 'post_install')
class TestError(common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mute_deprecation = mute_logger('odoo.addons.base.controllers.rpc')
        mute_deprecation.__enter__()
        cls.addClassCleanup(mute_deprecation.__exit__)

    def setUp(self):
        super(TestError, self).setUp()
        uid = self.ref("base.user_admin")

        self.xmlrpc_common = ServerProxy(f'{self.base_url()}/xmlrpc/2/common', transport=Transport(self.cr))
        self.xmlrpc_db = ServerProxy(f'{self.base_url()}/xmlrpc/2/db', transport=Transport(self.cr))
        self.xmlrpc_object = ServerProxy(f'{self.base_url()}/xmlrpc/2/object', transport=Transport(self.cr))
        self.rpc = partial(self.xmlrpc_object.execute, common.get_db_name(), uid, "admin")

        # Reset the admin's lang to avoid breaking tests due to admin not in English
        self.rpc("res.users", "write", [uid], {"lang": False})

    def test_01_create(self):
        """ Create: mandatory field not provided """
        self.rpc("test_rpc.model_b", "create", {"name": "B1"})
        try:
            with mute_logger("odoo.sql_db"):
                self.rpc("test_rpc.model_b", "create", {})
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn("Create/update: a mandatory field is not set.", e.faultString)
            self.assertIn(
                "Delete: another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model B (test_rpc.model_b)", e.faultString)
            self.assertIn("Field: Name (name)", e.faultString)

    def test_02_delete(self):
        """ Delete: NOT NULL and ON DELETE RESTRICT constraints """
        b1 = self.rpc("test_rpc.model_b", "create", {"name": "B1"})
        b2 = self.rpc("test_rpc.model_b", "create", {"name": "B2"})
        self.rpc("test_rpc.model_a", "create", {"name": "A1", "field_b1": b1, "field_b2": b2})

        try:
            with mute_logger("odoo.sql_db"):
                self.rpc("test_rpc.model_b", "unlink", b1)
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn(
                "another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model A (test_rpc.model_a)", e.faultString)
            self.assertIn("Constraint: test_rpc_model_a_field_b1_fkey", e.faultString)

        # Unlink b2 => ON DELETE RESTRICT constraint raises
        try:
            with mute_logger("odoo.sql_db"):
                self.rpc("test_rpc.model_b", "unlink", b2)
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn(
                " another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model A (test_rpc.model_a)", e.faultString)
            self.assertIn("Constraint: test_rpc_model_a_field_b2_fkey", e.faultString)
