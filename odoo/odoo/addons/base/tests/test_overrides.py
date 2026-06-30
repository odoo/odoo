# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestOverrides(TransactionCase):

    # Ensure all main ORM methods behavior works fine even on empty recordset
    # and that their returned value(s) follow the expected format.

    def test_creates(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            # with self.assertQueryCount(0):
            self.assertEqual(
                model_env.create([]), model_env.browse(),
                "Invalid create return value for model %s" % model_env._name)

    def test_writes(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            try:
                # with self.assertQueryCount(0):
                self.assertEqual(
                    model_env.browse().write({}), True,
                    "Invalid write return value for model %s" % model_env._name)
            except UserError:
                # skip models that should never be modified
                continue

    def test_default_get(self):
        for model_env in self.env.values():
            if model_env._transient:
                continue
            try:
                # with self.assertQueryCount(1):  # allow one query for the call to get_model_defaults.
                self.assertEqual(
                    model_env.browse().default_get([]), {},
                    "Invalid default_get return value for model %s" % model_env._name)
            except UserError:
                # skip "You must be logged in a Belgian company to use this feature" errors
                continue

    def test_unlink(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            # with self.assertQueryCount(0):
            self.assertEqual(
                model_env.browse().unlink(), True,
                "Invalid unlink return value for model %s" % model_env._name)
