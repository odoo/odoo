# -*- coding: utf-8 -*-

from odoo.tests import common
from odoo.tools.misc import mute_logger


class TestError(common.HttpCase):
    def setUp(self):
        super(TestError, self).setUp()
        self.o = self.xmlrpc_object
        self.db_name = common.get_db_name()
        # Reset the admin's lang to avoid breaking tests due to admin not in English
        self.o.execute(self.db_name, 1, "admin", "res.users", "write", [1], {"lang": False})

    def test_01_create(self):
        """ Create: mandatory field not provided """
        self.o.execute(self.db_name, 1, "admin", "test_rpc.model_b", "create", {"name": "B1"})
        try:
            with mute_logger("odoo.sql_db"):
                self.o.execute(self.db_name, 1, "admin", "test_rpc.model_b", "create", {})
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn("Create/update: a mandatory field is not set.", e.faultString)
            self.assertIn(
                "Delete: another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model B (test_rpc.model_b), Field: Name (name)", e.faultString)

    def test_02_delete(self):
        """ Delete: NOT NULL and ON DELETE RESTRICT constraints """
        b1 = self.o.execute(self.db_name, 1, "admin", "test_rpc.model_b", "create", {"name": "B1"})
        b2 = self.o.execute(self.db_name, 1, "admin", "test_rpc.model_b", "create", {"name": "B2"})
        self.o.execute(
            self.db_name, 1, "admin", "test_rpc.model_a", "create", {"name": "A1", "field_b1": b1, "field_b2": b2}
        )

        # Unlink b1 => NOT NULL constraint raises
        # FORWARD-PORT: in master, `required=True` implies `ondelete="restrict"`
        #               => the message should be the same than 'Unlink b2' case.
        try:
            with mute_logger("odoo.sql_db"):
                self.o.execute(self.db_name, 1, "admin", "test_rpc.model_b", "unlink", b1)
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn("Create/update: a mandatory field is not set.", e.faultString)
            self.assertIn(
                "Delete: another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model A (test_rpc.model_a), Field: required field (field_b1)", e.faultString)

        # Unlink b2 => ON DELETE RESTRICT constraint raises
        try:
            with mute_logger("odoo.sql_db"):
                self.o.execute(self.db_name, 1, "admin", "test_rpc.model_b", "unlink", b2)
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn(
                " another model requires the record being deleted. If possible, archive it instead.", e.faultString
            )
            self.assertIn(
                "Model: Model A (test_rpc.model_a), Constraint: test_rpc_model_a_field_b2_fkey", e.faultString
            )
